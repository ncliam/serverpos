function openerp_pos_uom(instance,module){
    var QWeb = instance.web.qweb;
	var _t = instance.web._t;
	var round_di = instance.web.round_decimals;
    var round_pr = instance.web.round_precision;
	
	module.Orderline_ncpos = module.Orderline.extend({
		
		// Change Unit of Sale
		change_uos: function(unit_id) {		
			//update unit and unit price
			this.default_uom = this.pos.units_by_id[this.product.uom_id[0]];
			this.uos_id = this.pos.units_by_id[unit_id];
			this.trigger('change',this);
		},
		
		// Get Unit Of Sale
		get_unit: function(){
            var unit_id = this.uos_id;
            if(unit_id){
            	return unit_id;
            }
            unit_id = this.product.uom_id;
            if(!unit_id){
                return undefined;
            }
            unit_id = unit_id[0];
            if(!this.pos){
                return undefined;
            }
            return this.pos.units_by_id[unit_id];
        },
        
        // Get unit price base on new UOM
        get_unit_price: function(){
            var unit_price = round_di(this.price || 0, this.pos.dp['Product Price']);
            if (this.uos_id && this.default_uom && this.uos_id.id != this.default_uom.id) {
            	unit_price = unit_price * this.uos_id.factor_inv * this.default_uom.factor;
            }
            return unit_price;
        },
        export_as_JSON: function() {
        	var uos_qty = this.get_quantity();
        	var uos_price = this.get_unit_price();
        	
        	var unit_price = round_di(this.price || 0, this.pos.dp['Product Price']);
        	var quantity = (uos_price * uos_qty) / unit_price;
        	
        	
            return {            	
                qty: quantity,                
                price_unit: unit_price,
                discount: this.get_discount(),
                product_id: this.get_product().id,
                uos: this.get_unit().id, // add UOS into orderline
                uos_qty: uos_qty,
                uos_price_unit: uos_price,
            };
        },
	});	
	
	module.Orderline = module.Orderline_ncpos;
    
	module.OrderWidget.include({
        render_orderline: function(orderline){
        	var el_node = this._super(orderline);
        	var select_control = el_node.getElementsByClassName("uos_selection")[0];
        	if (select_control != null && select_control != "undefined") {
	        	select_control.onchange = function() {
	        		orderline.change_uos(select_control.value);
	        	};
        	}
            return el_node;
        },
        
    });
}