# Create your views here.
from django.shortcuts import render_to_response
from django.http import Http404, HttpResponseRedirect
from django.template import TemplateDoesNotExist
from django.views.generic.simple import direct_to_template
import  urllib, json, base64, logging 
from base import auth, signals, annotations, utils_response as UR, models as M
from django.conf import settings
import string, random, forms
from random import choice
from django.core.mail.message import EmailMessage
from django.template.loader import render_to_string
id_log = "".join([ random.choice(string.ascii_letters+string.digits) for i in xrange(0,10)])
logging.basicConfig(level=logging.DEBUG,format='%(asctime)s %(levelname)s %(message)s', filename='/tmp/nb_pages_%s.log' % ( id_log,), filemode='a')


def on_serve_page(sender, **payload): 
    req = payload["req"]
    uid = payload["uid"]
    #print req.META
    #uid =  UR.getUserInfo(req, True)["id"]
    p={}
    p["client"] = req.META.get("REMOTE_HOST", None)
    p["ip"]     = req.META.get("REMOTE_ADDR", None)
    p["referer"]= req.META.get("HTTP_REFERER", None)
    p["path"]   = req.get_full_path()
    annotations.page_served(uid, p)
if settings.MONITOR.get("PAGE_SERVED", False): 
    signals.page_served.connect(on_serve_page, weak=False)




def __serve_page(req, tpl, allow_guest=False, nologin_url=None): 
    """Serve the template 'tpl' if user is DB or allow_guest is True. If not, serve the welcome/login screen"""
    o           = {} #for template
    user       = UR.getUserInfo(req, allow_guest)
    if user is None:
        redirect_url = nologin_url if nologin_url is not None else ("/login?next=%s" % (req.META.get("PATH_INFO","/"),))
        return HttpResponseRedirect(redirect_url)
    if user.guest is False and (user.firstname is None or user.lastname is None): 
        return HttpResponseRedirect("/enteryourname?ckey=%s" % (user.confkey,)) 
    user = UR.model2dict(user, {"ckey": "confkey", "email": None, "firstname": None, "guest": None, "id": None, "lastname": None, "password": None, "valid": None}) 
    signals.page_served.send("page", req=req, uid=user["id"])
    r = render_to_response(tpl, {"o": o}, mimetype='application/xhtml+xml')
    r.set_cookie("userinfo", urllib.quote(json.dumps(user)), 1e9)
    return r

def __serve_page_old(req, tpl, allow_guest=False): 
    """ 
    For compatibility purposes. 
    this function serves the template 'tpl' if we find correct authentication. If we don't, we serve the default login screen"""
    email = req.COOKIES["email"] if "email" in req.COOKIES else None
    password = req.COOKIES["password"] if "password" in req.COOKIES else None
    o = {}
    template = settings.LOGIN_TEMPLATE
    invite_key = None

    if "invite_key" in req.GET:
        invite_key = req.GET["invite_key"]
    elif "invite_key" in req.COOKIES and "logout" not in req.COOKIES: 
        invite_key = req.COOKIES["invite_key"]
        logging.debug("invite_key from cookie %s" % (invite_key, ))

    if invite_key is not None: 
        #see if we have such a invite_key on file:
        invite = auth.confirmInvite(invite_key)
        #logging.debug("invite %s" % (invite, ))
        if invite is None:
            return UR.prepare_response({}, 1,  "NOT ALLOWED")      
        o["EMAIL"]=invite.user.email
        o["PASSWORD"]=base64.b64encode(invite.user.password)
        o["FULLNAME"] = invite.user.email
        o["UID"] = invite.user.id
        o["INVITE_KEY"] = invite.key
        template = tpl
    elif email is not None and password is not None:
        o["EMAIL"]=email
        o["FULLNAME"]=email
        o["PASSWORD"]=password
        uid = auth.checkPassword(email, password)
        o["UID"]=str(uid)
        if uid is not None: 
            valid_invite_key = auth.get_valid_invite_key(uid)
            if valid_invite_key is not None:
                o["INVITE_KEY"] = valid_invite_key
            template = tpl
        else: 
            o["LOGIN_MSG"] = "wrong email/password, please retry!"
    r = render_to_response(template, {"o": o}, mimetype='application/xhtml+xml')
    if "INVITE_KEY" in o: 
        r.set_cookie("invite_key", o["INVITE_KEY"], 1e9)
        r.set_cookie("screenname", o["EMAIL"], 1e9)
    elif "invite_key" in req.COOKIES: 
        r.delete_cookie("invite_key")
    r.set_cookie("uid", o["UID"] if "UID" in o else 0, 1e9) #this is just to inform the client-side app, don't use it for auth. purposes
    if "logout" in req.COOKIES: 
        r.delete_cookie("logout")
    return r

def index(req): 
    return __serve_page(req, settings.DESKTOP_TEMPLATE, False, "/welcome")
   
def collage(req): 
    return __serve_page(req, settings.COLLAGE_TEMPLATE)

def admin(req): 
    return __serve_page(req, settings.ADMIN_TEMPLATE)

def alpha(req): 
    return __serve_page(req, settings.ALPHA_TEMPLATE)

def feedback(req): 
    return __serve_page_old(req, settings.FEEDBACK_TEMPLATE)

def feedback_alpha(req): 
    return __serve_page_old(req, settings.FEEDBACK_ALPHA_TEMPLATE)

def dev_desktop(req, n): 
    return __serve_page(req, settings.DEV_DESKTOP_TEMPLATE % (n,))

def source(req, n, allow_guest=False):
    return __serve_page(req, settings.SOURCE_TEMPLATE, allow_guest)

def your_settings(req): 
    return __serve_page(req, 'web/your_settings.html')

def draft(req, tplname):
    try:
        r = render_to_response("drafts/%s.html" % tplname, {}, mimetype='application/xhtml+xml')
        return r
    except TemplateDoesNotExist:
        raise Http404()
 
def newsite(req):
    import base.models as M, random, string 
    form                = None
    auth_user           = UR.getUserInfo(req)
    ensemble_form       = None
    user_form           = None
    if auth_user is not None: 
        return HttpResponseRedirect("/admin")
    if req.method == 'POST':
        user            = M.User(confkey="".join([choice(string.ascii_letters+string.digits) for i in xrange(0,32)]))
        ensemble        = M.Ensemble()
        user_form       = forms.UserForm(req.POST, instance=user)
        ensemble_form   = forms.EnsembleForm(req.POST, instance=ensemble)
        if user_form.is_valid() and ensemble_form.is_valid():             
            user_form.save()
            ensemble.invitekey =  "".join([ random.choice(string.ascii_letters+string.digits) for i in xrange(0,50)])      
            ensemble_form.save()
            m = M.Membership(user=user, ensemble=ensemble, admin=True)
            m.save()
            p = {"tutorial_url": settings.GUEST_TUTORIAL_URL, "conf_url": "http://%s/admin?ckey=%s" %(settings.NB_SERVERNAME, user.confkey), "firstname": user.firstname, "email": user.email, "password": user.password }
            email = EmailMessage(
                "Welcome to NB, %s" % (user.firstname),
                render_to_string("email/confirm_newsite", p), 
                settings.EMAIL_FROM, 
                (user.email, ), 
                (settings.EMAIL_BCC, ))
            email.send()
            return HttpResponseRedirect('/newsite_thanks')       
    else: 
        user_form       = forms.UserForm()
        ensemble_form   = forms.EnsembleForm()
    return render_to_response("web/newsite.html", {"user_form": user_form, "ensemble_form": ensemble_form})


def enter_your_name(req):    
    import base.models as M
    user       = UR.getUserInfo(req, False)
    if user is None:
        redirect_url = "/login?next=%s" % (req.META.get("PATH_INFO","/"),)
        return HttpResponseRedirect(redirect_url)
    user_form = forms.EnterYourNameUserForm(instance=user)        
    if req.method == 'POST':
        user_form = forms.EnterYourNameUserForm(req.POST, instance=user)
        if user_form.is_valid():             
            user_form.save()            
            return HttpResponseRedirect("/?ckey=%s" % (user.confkey,))         
    return render_to_response("web/enteryourname.html", {"user_form": user_form})



def comment(req, id_comment): 
    #id_comment = int(id_comment)
    c = M.Comment.objects.get(pk=id_comment)    
    #id_source = annotations.getSourceForComment(id_comment)
    #[id_comment]
    org=("&org="+req.GET["org"]) if "org" in req.GET else ""
    return HttpResponseRedirect("/f/%s?c=%s%s" % (c.location.source.id, id_comment, org))
    
def invite(req): 
    pass #SACHA TODO

def logout(req): 
    o = {}
    r = render_to_response("web/logout.html", {"o": o})
    r.delete_cookie("userinfo")
    r.delete_cookie("ckey")
    return r

def confirm_invite(req):        
    invite_key  = req.GET.get("invite_key", None)
    invite      = M.Invite.objects.get(key=invite_key)
    m = M.Membership.objects.filter(user=invite.user, ensemble=invite.ensemble)
    if m.count() > 0:
        m = m[0]
    else: 
        m = M.Membership(user=invite.user, ensemble=invite.ensemble)
    m.admin = invite.admin
    m.save()
    if invite.user.valid == False:
        invite.user.valid=True
        invite.user.save()
    r = render_to_response("web/confirm_invite.html", {"o": m})
    return r

def subscribe(req):
    key     = req.GET.get("key", "")
    e       = M.Ensemble.objects.get(invitekey=key)
    if not e.use_invitekey: 
        return HttpResponseRedirect("/notallowed")    
    auth_user       = UR.getUserInfo(req)
    user = None
    P = {"ensemble": e, "key": key}   
    if req.method == 'POST':
        if auth_user is None:
            user = M.User(confkey="".join([choice(string.ascii_letters+string.digits) for i in xrange(0,32)]))
            user_form = forms.UserForm(req.POST, instance=user)
            if user_form.is_valid(): 
                user_form.save()  
                m = M.Membership(user=user, ensemble=e)
                m.save() #membership exists but user is still invalid until has confirmed their email
                p = {"tutorial_url": settings.GUEST_TUTORIAL_URL, "conf_url": "%s://%s/?ckey=%s" %(settings.PROTOCOL, settings.NB_SERVERNAME, user.confkey), "firstname": user.firstname, "email": user.email, "password": user.password }
                email = EmailMessage(
                "Welcome to NB, %s" % (user.firstname,),
                render_to_string("email/confirm_subscribe", p), 
                settings.EMAIL_FROM, 
                (user.email, ), 
                (settings.EMAIL_BCC, ))
                email.send()
                return HttpResponseRedirect('/subscribe_thanks')
            else: 
                P["form"] = forms.UserForm(req.POST, instance=user)
                return render_to_response("web/subscribe_newuser.html", P)   
        else: 
            user = auth_user
            m = M.Membership.objects.filter(user=user, ensemble=e)
            if m.count() ==0: 
                m = M.Membership(user=user, ensemble=e)
                m.save()
            return HttpResponseRedirect('/')
        #user_form = forms.EnterYourNameUserForm(req.POST, instance=user)        
    else: 
        if auth_user is not None:
            P["user"] = auth_user
            P["form"] = forms.UserForm(instance=user)
            return render_to_response("web/subscribe_existinguser.html", P)
        else:        
            P["form"] = forms.UserForm()
            return render_to_response("web/subscribe_newuser.html", P)
                    
    


def properties_ensemble(req, id):
    user       = UR.getUserInfo(req)
    if user is None: 
        return HttpResponseRedirect("/login?next=%s" % (req.META.get("PATH_INFO","/"),))
    if not auth.canEditEnsemble(user.id, id):
        return HttpResponseRedirect("/notallowed")
    ensemble = M.Ensemble.objects.get(pk=id)
    ensemble_form = None
    if req.method=="POST": 
        ensemble_form = forms.EnsembleForm(req.POST, instance=ensemble)  
        if ensemble_form.is_valid(): 
            ensemble_form.save()   
            return HttpResponseRedirect('/admin')   
    else: 
        ensemble_form = forms.EnsembleForm(instance=ensemble)
    return render_to_response("web/properties_ensemble.html", {"form": ensemble_form, "conf_url":  "%s://%s/subscribe?key=%s" %(settings.PROTOCOL, settings.NB_SERVERNAME, ensemble.invitekey)})


def properties_ensemble_users(req, id):
    user       = UR.getUserInfo(req)
    if user is None: 
        return HttpResponseRedirect("/login?next=%s" % (req.META.get("PATH_INFO","/"),))
    if not auth.canEditEnsemble(user.id, id):
        return HttpResponseRedirect("/notallowed")
    ensemble = M.Ensemble.objects.get(pk=id)
    memberships = M.Membership.objects.filter(ensemble=ensemble)
    pendingconfirmations = memberships.filter(user__in=M.User.objects.filter(valid=False), deleted=False)
    real_memberships = memberships.filter(user__in=M.User.objects.filter(valid=True), deleted=False)    
    pendinginvites = M.Invite.objects.filter(ensemble=ensemble).exclude(user__id__in=real_memberships.values("user_id"))    
    return render_to_response("web/properties_ensemble_users.html", {"ensemble": ensemble, "memberships": real_memberships, "pendinginvites": pendinginvites, "pendingconfirmations": pendingconfirmations})

def spreadsheet(req):
    return __serve_page(req, settings.SPREADSHEET_TEMPLATE, False, "/login?next=%s" % (req.get_full_path(),))
#   
# UR.getUserInfo(req)
#    if user is None: 
#        return HttpResponseRedirect("/login?next=%s" % (req.get_full_path(),))
#    if "id_ensemble" not in req.GET: 
#        from django.http import HttpResponse
#        return HttpResponse("missing id_ensemble")
#    id_ensemble = req.GET["id_ensemble"]
#    if not auth.canEditEnsemble(user.id,id_ensemble):
#        return HttpResponseRedirect("/notallowed")
#       
