#The COPYRIGHT file at the top level of this repository contains the full
#copyright notices and license terms.
import datetime
from datetime import timedelta
from trytond.model import Model, ModelView, ModelSQL, Workflow, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Bool, Eval, Equal, If, In
from trytond.transaction import Transaction

__all__ = ['Configuration', 'ConfigurationCompany', 'Move',
    'SupplyRequest', 'SupplyRequestLine']
__metaclass__ = PoolMeta

_STATES = {
    'readonly': Eval('state') != 'draft',
}
_DEPENDS = ['state']


class Configuration:
    __name__ = 'stock.configuration'

    supply_request_sequence = fields.Function(fields.Many2One('ir.sequence',
            'Supply Request Reference Sequence', required=True, domain=[
                ('company', 'in',
                    [Eval('context', {}).get('company', -1), None]),
                ('code', '=', 'stock.supply_request'),
                ]),
        'get_company_config', setter='set_company_config')
    default_request_from_warehouse = fields.Function(
        fields.Many2One('stock.location', 'Default Request From Warehouse',
            domain=[('type', '=', 'warehouse')]),
        'get_company_config', setter='set_company_config')

    @classmethod
    def get_company_config(self, configs, names):
        pool = Pool()
        CompanyConfig = pool.get('stock.configuration.company')

        company_id = Transaction().context.get('company')
        company_configs = CompanyConfig.search([
                ('company', '=', company_id),
                ])

        res = {}
        for fname in names:
            res[fname] = {
                configs[0].id: None,
                }
            if company_configs:
                val = getattr(company_configs[0], fname)
                if isinstance(val, Model):
                    val = val.id
                res[fname][configs[0].id] = val
        return res

    @classmethod
    def set_company_config(self, configs, name, value):
        pool = Pool()
        CompanyConfig = pool.get('stock.configuration.company')

        company_id = Transaction().context.get('company')
        company_configs = CompanyConfig.search([
                ('company', '=', company_id),
                ])
        if company_configs:
            company_config = company_configs[0]
        else:
            company_config = CompanyConfig(company=company_id)
        setattr(company_config, name, value)
        company_config.save()


class ConfigurationCompany(ModelSQL):
    'Stock Configuration by Company'
    __name__ = 'stock.configuration.company'

    company = fields.Many2One('company.company', 'Company', required=True,
        ondelete='CASCADE', select=True)
    default_request_from_warehouse = fields.Many2One('stock.location',
        'Default Request From Warehouse', domain=[('type', '=', 'warehouse')])
    supply_request_sequence = fields.Many2One('ir.sequence',
        'Supply Request Reference Sequence', domain=[
            ('company', 'in', [Eval('company'), None]),
            ('code', '=', 'stock.supply_request'),
            ], depends=['company'])

    @staticmethod
    def default_company():
        return Transaction().context.get('company')


class Move():
    __name__ = 'stock.move'

    @classmethod
    def _get_origin(cls):
        models = super(Move, cls)._get_origin()
        models.append('stock.supply_request.line')
        return models


class SupplyRequest(Workflow, ModelSQL, ModelView):
    '''Supply Request
    Manage requests of materials between warehouses.'''
    __name__ = 'stock.supply_request'
    _rec_name = 'reference'

    company = fields.Many2One('company.company', 'Company', required=True,
        domain=[
            ('id', If(In('company', Eval('context', {})), '=', '!='),
                Eval('context', {}).get('company', -1)),
            ], states=_STATES, depends=_DEPENDS)
    reference = fields.Char('Reference', readonly=True, select=True)
    date = fields.DateTime('Date', required=True, states=_STATES,
        depends=_DEPENDS)
    from_warehouse = fields.Many2One('stock.location', 'From Warehouse',
        domain=[
            ('type', '=', 'warehouse'),
            ], select=True, required=True, states=_STATES, depends=_DEPENDS)
    to_warehouse = fields.Many2One('stock.location', 'To Warehouse', domain=[
            ('type', '=', 'warehouse'),
            ], select=True, required=True, states=_STATES, depends=_DEPENDS)
    lines = fields.One2Many('stock.supply_request.line', 'request', 'Lines',
        states=_STATES, depends=_DEPENDS)
    note = fields.Text('Note', states=_STATES, depends=_DEPENDS)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ], 'State', readonly=True, required=True, select=True)

    @classmethod
    def __setup__(cls):
        super(SupplyRequest, cls).__setup__()
        cls._sql_constraints += [
            ('check_from_to_warehouses',
                'CHECK(from_warehouse != to_warehouse)',
                'Source and destination warehouse must be different'),
            ]
        cls._transitions |= set((
                ('draft', 'confirmed'),
                ))
        cls._buttons.update({
                'confirm': {
                    'invisible': Eval('state') != 'draft',
                    },
                })

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

    @staticmethod
    def default_date():
        return datetime.datetime.now()

    @staticmethod
    def default_from_warehouse():
        pool = Pool()
        Config = pool.get('stock.configuration')
        config = Config(1)
        if config.default_request_from_warehouse:
            return config.default_request_from_warehouse.id
        return None

    @staticmethod
    def default_state():
        return 'draft'

    def get_rec_name(self, name):
        return (self.reference or str(self.id)
            + ' - ' + str(self.date))

    @classmethod
    @ModelView.button
    @Workflow.transition('confirmed')
    def confirm(cls, requests):
        for request in requests:
            for line in request.lines:
                move = line.get_move()
                move.save()
                line.move = move
                line.save()
            request.set_reference()

    def set_reference(self):
        '''
        Fill the reference field with the warehouse's requests sequence
        '''
        pool = Pool()
        Config = pool.get('stock.configuration')
        Sequence = pool.get('ir.sequence')

        config = Config(1)
        if not self.reference:
            reference = Sequence.get_id(config.supply_request_sequence.id)
            self.reference = reference
            self.save()

    @classmethod
    def copy(cls, requests, default=None):
        if default is None:
            default = {}
        default = default.copy()
        default['reference'] = None
        default['state'] = 'draft'
        return super(SupplyRequest, cls).copy(requests, default=default)


class SupplyRequestLine(ModelSQL, ModelView):
    'Supply Request Line'
    __name__ = 'stock.supply_request.line'

    request = fields.Many2One('stock.supply_request', 'Request', required=True,
        ondelete='CASCADE')
    company = fields.Function(fields.Many2One('company.company', 'Company'),
        'get_company', searcher='search_company')
    product = fields.Many2One('product.product', 'Product', domain=[
            ('type', '!=', 'service'),
            ], on_change=['product', 'unit', 'unit_digits'], required=True)
    unit = fields.Function(fields.Many2One('product.uom', 'Unit'),
        'get_unit')
    unit_digits = fields.Function(fields.Integer('Unit Digits'),
        'get_unit')
    quantity = fields.Float('Quantity', digits=(16, Eval('unit_digits', 2)),
        depends=['unit_digits'], required=True)
    to_location = fields.Many2One('stock.location', 'To Location',
        required=True, domain=[
            ('type', '=', 'storage'),
            If(Bool(Eval('_parent_request', {}).get('to_warehouse', 0)),
                ('parent', 'child_of', [Eval('_parent_request',{}).get(
                        'to_warehouse',0)]),
                ()),
            ], depends=['to_warehouse'])
    delivery_date = fields.Date("Delivery Date", required=True)
    move = fields.Many2One('stock.move', 'Reserve', readonly=True, states={
            'required': Equal(Eval('_parent_request.state'), 'confirmed'),
            })
    supply_state = fields.Function(fields.Selection([
                ('pending', 'Pending'),
                ('in_progress', 'In Progress'),
                ('done', 'Done'),
                ('cancel', 'Canceled'),
                ], 'Supply State'),
        'get_supply_state')

    @staticmethod
    def default_delivery_date():
        return datetime.date.today() + timedelta(days=2)

    def get_company(self, name):
        return self.request and self.request.company.id

    @classmethod
    def search_company(cls, name, clause):
        return [('request.%s' % name,) + tuple(clause[1:])]

    def on_change_with_to_warehouse(self, name=None):
        if self.request and self.request.to_warehouse:
            return self.request.to_warehouse.id
        return None

    def on_change_product(self):
        res = {}
        if self.product:
            res['unit'] = self.product.default_uom.id
            res['unit.rec_name'] = self.product.default_uom.rec_name
            res['unit_digits'] = self.product.default_uom.digits
        return res

    @classmethod
    def get_unit(cls, lines, names):
        res = {}
        for line in lines:
            if 'unit' in names:
                res.setdefault('unit', {})[line.id] = (
                    line.product.default_uom.id)
            if 'unit_digits' in names:
                res.setdefault('unit_digits', {})[line.id] = (
                    line.product.default_uom.digits)
        return res

    def get_supply_state(self, name):
        if not self.move:
            return 'pending'
        if self.move.state in ('done', 'cancel'):
            return self.move.state
        return 'in_progress'

    def get_move(self):
        '''
        Return move for the line
        '''
        pool = Pool()
        Move = pool.get('stock.move')

        move = Move()
        move.product = self.product.id
        move.uom = self.unit.id
        move.quantity = self.quantity
        move.from_location = self.request.from_warehouse.storage_location
        move.to_location = self.to_location
        move.planned_date = self.delivery_date
        move.company = self.company
        move.origin = self
        return move

    @classmethod
    def copy(cls, lines, default=None):
        if default is None:
            default = {}
        default = default.copy()
        default['move'] = None
        return super(SupplyRequestLine, cls).copy(lines, default=default)
