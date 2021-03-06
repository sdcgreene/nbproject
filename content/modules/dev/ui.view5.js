/* View Plugin v.5
 * Depends:
 *	ui.core.js
 *      concierge
 Author 
 Sacha Zyto (sacha@csail.mit.edu) 

 License
 Copyright (c) 2010 Massachusetts Institute of Technology.
 MIT License (cf. MIT-LICENSE.txt or http://www.opensource.org/licenses/mit-license.php)

*/
(function($) {   
    /*
     * The view object
     * options.headless set to false if the view is not meant to be displayed
     */
    var V_OBJ = {
	HEIGHT_MARGIN: 5,
	SERVICE: null,
	_create: function() {
	    var self = this;
	    var init = true;
	    // initialization from scratch
	    if (init) {			
		if (self.options.provides){
		    $.concierge.addProviders(self.element[0].id, self.options.provides);
		}
		if (self.options.listens){
		    $.concierge.addListeners(self, self.options.listens);
		}
		if (self.options.transitions){
		    $.concierge.setTransitions(self.element[0].id, self.options.transitions);
		}
		if (!(self.options.headless)){
		    self.element.addClass("view");

		    //implement a concept of "active view"
		    self.element.mouseenter(function(evt){		
			    $.concierge.activeView = self;
			    $("div.view").removeClass("active-view");
			    self.element.addClass("active-view");
			});

		    //register for perspective events: 
		    self.element.closest("div.perspective").bind("resize_perspective", function(evt,directions){
			    self.repaint();
			});
		    
		}
		// $.D("setting view ", this.element[0].id, " to " , this);
		$.concierge.views[this.element[0].id]=this;
	    }
	}, 
	defaultHandler: function(evt){
	    $.D("[View]: default handler... override me !, evt=", evt);
	},
	beforeMove: function(evt){
	    $.D("[View]: default beforemove... override me !, evt=", evt);
	},
	afterMove: function(evt){
	    $.D("[View]: default aftermmove... override me !, evt=", evt);
	},
	set_model: function(model){
	    this._model = model;
	    //for now, we don't register to receive any particular updates.
	    model.register($.ui.view.prototype.get_adapter.call(this),  {});
	},
	repaint: function(){
	    //PRE: not a headless view
	    var self = this;
	    /*
	      var outerview = self.element.parent("div.outerview");	    
	      var vp = outerview.parent("div.viewport");
	      if(outerview.length && vp.length){
	      //make sure we get offset of a visible component: 
	      var y0 = vp.children(".outerview:visible").offset().top - vp.offset().top;
	      outerview.height(vp.height()-y0);
	      }
	    */
	    self._update();
	},
	_update: function(){
	    this.element.height(this.element.parent().height());
	    this.element.width(this.element.parent().width());
	    this._expand();
	},
	_keydown: function(event){
	    $.D("[view._keydown] override me for ", this.element);
 	}, 
	get_adapter: function(){
	    /* enables a view to be called by the methods of an mvc.model */
	    var self = this;
	    var adapter = {
		update: function(action, payload, items_fieldname){
		    self.update(action, payload, items_fieldname);
		}
	    };
	    return adapter;
	},
	close: function(){
	    var self = this;
	    $.D("[View]: default closer ...override me !");
	    delete $.concierge.views[self.element[0].id];
	},
	provides: function(){
	    var self = this;
	    return self.options.provides || {};
	},
	select: function(){
	    $.D("[view]: selected ", this.element[0].id);
	}, 
	sayHello: function(){
	    $.D("Hello, I'm view ", this.element.id);
	}, 
	update: function(action, payload, items_fieldname){
	    $.D("[view] updating view:, ", action, payload);
	}, 
	keyboard_grabber: function(){
	    return $("input.focusgrabber", this.element);
	},
	_expand: function(){
	    var $expand	= $(this.options.expand);
	    if ($expand.length){
		var s0		= $expand.offset().top+parseInt($expand.css("margin-top")) - this.element.offset().top;
		$expand.height(this.element.height() - s0);
	    }
	}
    };
    
    $.widget("ui.view",V_OBJ );
    $.ui.view.prototype.options = {};
    $.extend($.ui.view, {
	    version: '1.8',
		service: null, 
		provides: null,
		listens: null, 
		transitions: null,
		});
})(jQuery);
