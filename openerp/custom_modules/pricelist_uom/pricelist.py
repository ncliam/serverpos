# -*- coding: utf-8 -*-
#################################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 Julius Network Solutions SARL <contact@julius.fr>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#################################################################################

from openerp.osv import fields, osv
from openerp.tools.translate import _

class product_pricelist(osv.osv):
    _inherit = "product.pricelist"
    
    def price_get_multi(self, cr, uid, ids, products_by_qty_by_partner, context=None):
        return dict((key, dict((key, price[0]) for key, price in value.items())) for key, value in self.price_rule_get_multi(cr, uid, ids, products_by_qty_by_partner, context=context).items())

    def price_rule_get_multi(self, cr, uid, ids, products_by_qty_by_partner, context=None):
        """multi products 'price_get'.
           @param ids:
           @param products_by_qty:
           @param partner:
           @param context: {
             'date': Date of the pricelist (%Y-%m-%d),}
           @return: a dict of dict with product_id as key and a dict 'price by pricelist' as value
        """
        if not ids:
            ids = self.pool.get('product.pricelist').search(cr, uid, [], context=context)
        results = {}
        for pricelist in self.browse(cr, uid, ids, context=context):
            subres = self._price_rule_get_multi(cr, uid, pricelist, products_by_qty_by_partner, context=context)
            for product_id,price in subres.items():
                results.setdefault(product_id, {})
                results[product_id][pricelist.id] = price
        return results

    def _price_get_multi(self, cr, uid, pricelist, products_by_qty_by_partner, context=None):
        return dict((key, price[0]) for key, price in self._price_rule_get_multi(cr, uid, pricelist, products_by_qty_by_partner, context=context).items())
    
    def _price_rule_get_multi(self, cr, uid, pricelist, products_by_qty_by_partner, context=None):
        context = context or {}
        date = context.get('date') or time.strftime('%Y-%m-%d')
        date = date[0:10]

        products = map(lambda x: x[0], products_by_qty_by_partner)
        currency_obj = self.pool.get('res.currency')
        product_obj = self.pool.get('product.template')
        product_uom_obj = self.pool.get('product.uom')
        price_type_obj = self.pool.get('product.price.type')

        if not products:
            return {}

        version = False
        for v in pricelist.version_id:
            if ((v.date_start is False) or (v.date_start <= date)) and ((v.date_end is False) or (v.date_end >= date)):
                version = v
                break
        if not version:
            raise osv.except_osv(_('Warning!'), _("At least one pricelist has no active version !\nPlease create or activate one."))
        categ_ids = {}
        uos_ids = {}
        for p in products:
            categ = p.categ_id
            uos_id = context.get('uom') or p.uom_id.id
            while categ:
                categ_ids[categ.id] = True
                categ = categ.parent_id
            
            if uos_id:
                uos_ids[uos_id] = True
                    
            
        categ_ids = categ_ids.keys()
        uos_ids = uos_ids.keys()

        is_product_template = products[0]._name == "product.template"
        if is_product_template:
            prod_tmpl_ids = [tmpl.id for tmpl in products]
            # all variants of all products
            prod_ids = [p.id for p in
                        list(chain.from_iterable([t.product_variant_ids for t in products]))]
        else:
            prod_ids = [product.id for product in products]
            prod_tmpl_ids = [product.product_tmpl_id.id for product in products]

        # Load all rules
        cr.execute(
            'SELECT i.id '
            'FROM product_pricelist_item AS i '
            'WHERE (product_tmpl_id IS NULL OR product_tmpl_id = any(%s)) '
                'AND (product_id IS NULL OR (product_id = any(%s))) '
                'AND ((categ_id IS NULL) OR (categ_id = any(%s))) '
                'AND ((uom_id IS NULL) OR (uom_id = any(%s))) '
                'AND (price_version_id = %s) '
            'ORDER BY sequence, min_quantity desc',
            (prod_tmpl_ids, prod_ids, categ_ids, uos_ids, version.id))
        
        item_ids = [x[0] for x in cr.fetchall()]
        items = self.pool.get('product.pricelist.item').browse(cr, uid, item_ids, context=context)

        price_types = {}

        results = {}
        for product, qty, partner in products_by_qty_by_partner:
            results[product.id] = 0.0
            rule_id = False
            price = product.list_price

            # Final unit price is computed according to `qty` in the `qty_uom_id` UoM.
            # An intermediary unit price may be computed according to a different UoM, in
            # which case the price_uom_id contains that UoM.
            # The final price will be converted to match `qty_uom_id`.
            qty_uom_id = context.get('uom') or product.uom_id.id
            price_uom_id = product.uom_id.id
            qty_in_product_uom = qty
            qty_in_rule_uom = qty
            if qty_uom_id != product.uom_id.id:
                try:
                    qty_in_product_uom = product_uom_obj._compute_qty(
                        cr, uid, context['uom'], qty, product.uom_id.id or product.uos_id.id)
                except except_orm:
                    # Ignored - incompatible UoM in context, use default product UoM
                    pass

            for rule in items:
                if rule.uom_id:
                    if qty_uom_id != rule.uom_id.id:
                        continue
                    else:
                        try:
                            qty_in_rule_uom = product_uom_obj._compute_qty(
                                cr, uid, qty_uom_id, qty, rule.uom_id.id)
                        except except_orm:
                            # Ignored - incompatible UoM in context, use default product UoM
                            pass
                    
                if rule.min_quantity:
                    
                    if rule.uom_id and qty_in_rule_uom < rule.min_quantity:                        
                        continue
                    elif not rule.uom_id and qty_in_product_uom < rule.min_quantity:
                        continue
                    
                if is_product_template:
                    if rule.product_tmpl_id and product.id != rule.product_tmpl_id.id:
                        continue
                    if rule.product_id and not (product.product_variant_count == 1 and product.product_variant_ids[0].id == rule.product_id.id):
                        # product rule acceptable on template if has only one variant
                        continue
                else:
                    if rule.product_tmpl_id and product.product_tmpl_id.id != rule.product_tmpl_id.id:
                        continue
                    if rule.product_id and product.id != rule.product_id.id:
                        continue

                if rule.categ_id:
                    cat = product.categ_id
                    while cat:
                        if cat.id == rule.categ_id.id:
                            break
                        cat = cat.parent_id
                    if not cat:
                        continue
                    
                

                if rule.base == -1:
                    if rule.base_pricelist_id:
                        price_tmp = self._price_get_multi(cr, uid,
                                rule.base_pricelist_id, [(product,
                                qty, partner)], context=context)[product.id]
                        ptype_src = rule.base_pricelist_id.currency_id.id
                        price_uom_id = qty_uom_id
                        price = currency_obj.compute(cr, uid,
                                ptype_src, pricelist.currency_id.id,
                                price_tmp, round=False,
                                context=context)
                elif rule.base == -2:
                    seller = False
                    for seller_id in product.seller_ids:
                        if (not partner) or (seller_id.name.id != partner):
                            continue
                        seller = seller_id
                    if not seller and product.seller_ids:
                        seller = product.seller_ids[0]
                    if seller:
                        qty_in_seller_uom = qty
                        seller_uom = seller.product_uom.id
                        if qty_uom_id != seller_uom:
                            qty_in_seller_uom = product_uom_obj._compute_qty(cr, uid, qty_uom_id, qty, to_uom_id=seller_uom)
                        price_uom_id = seller_uom
                        for line in seller.pricelist_ids:
                            if line.min_quantity <= qty_in_seller_uom:
                                price = line.price

                else:
                    if rule.base not in price_types:
                        price_types[rule.base] = price_type_obj.browse(cr, uid, int(rule.base))
                    price_type = price_types[rule.base]

                    # price_get returns the price in the context UoM, i.e. qty_uom_id
                    price_uom_id = qty_uom_id
                    if rule.uom_id:
                        price_uom_id = rule.uom_id.id
                        
                    price = currency_obj.compute(
                            cr, uid,
                            price_type.currency_id.id, pricelist.currency_id.id,
                            product_obj._price_get(cr, uid, [product], price_type.field, context=context)[product.id],
                            round=False, context=context)

                if price is not False:
                    price_limit = price
                    price = price * (1.0+(rule.price_discount or 0.0))
                    if rule.price_round:
                        price = tools.float_round(price, precision_rounding=rule.price_round)

                    convert_to_price_uom = (lambda price: product_uom_obj._compute_price(
                                                cr, uid, product.uom_id.id,
                                                price, price_uom_id))
                    if rule.price_surcharge:
                        price_surcharge = convert_to_price_uom(rule.price_surcharge)
                        price += price_surcharge

                    if rule.price_min_margin:
                        price_min_margin = convert_to_price_uom(rule.price_min_margin)
                        price = max(price, price_limit + price_min_margin)

                    if rule.price_max_margin:
                        price_max_margin = convert_to_price_uom(rule.price_max_margin)
                        price = min(price, price_limit + price_max_margin)

                    rule_id = rule.id
                break

            # Final price conversion to target UoM
            price = product_uom_obj._compute_price(cr, uid, price_uom_id, price, qty_uom_id)

            results[product.id] = (price, rule_id)
        return results
    
    def price_get(self, cr, uid, ids, prod_id, qty, partner=None, context=None):
        return dict((key, price[0]) for key, price in self.price_rule_get(cr, uid, ids, prod_id, qty, partner=partner, context=context).items())

    def price_rule_get(self, cr, uid, ids, prod_id, qty, partner=None, context=None):
        product = self.pool.get('product.product').browse(cr, uid, prod_id, context=context)
        res_multi = self.price_rule_get_multi(cr, uid, ids, products_by_qty_by_partner=[(product, qty, partner)], context=context)
        res = res_multi[prod_id]
        return res

class product_pricelist_item(osv.osv):
    _inherit = 'product.pricelist.item'
    
    _columns = {
        'uom_id': fields.many2one('product.uom', 'Unit of Measure', ondelete='cascade', help="Specify a product UoM if this rule only applies to one product with UoM. Keep empty otherwise."),
    }
    
    def product_id_change(self, cr, uid, ids, product_id, context=None):
        values = super(product_pricelist_item, self).product_id_change(cr, uid, ids, product_id, context=context)
        if not values:
            values = {} 
        if not values.has_key('domain'):
            values['domain'] = {}
            
        domain = {}
        
        return values
        
class product_template(osv.osv):
    _name = 'product.template'
    _inherit = 'product.template'
    
    _columns = {        
        'uom_ids': fields.many2many('product.uom', 'product_uom_rel', 'product_tmpl_id', 'uom_id', 'Allowance UoM'),
    }