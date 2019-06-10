# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from datetime import datetime, timedelta
from trytond.model import Model, ModelView, ModelSQL, Workflow, Check, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Bool, Eval, Equal, If, In
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.i18n import gettext

__all__ = ['Configuration', 'ConfigurationCompany', 'Move', 'ShipmentInternal',
    'SupplyRequest', 'SupplyRequestLine']

_STATES = {
    'readonly': Eval('state') != 'draft',
}
_DEPENDS = ['state']


class Configuration(metaclass=PoolMeta):
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
    def get_company_config(cls, configs, names):
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
    def set_company_config(cls, configs, name, value):
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


class Move(metaclass=PoolMeta):
    __name__ = 'stock.move'

    @classmethod
    def _get_origin(cls):
        models = super(Move, cls)._get_origin()
        models.append('stock.supply_request.line')
        return models


class ShipmentInternal(metaclass=PoolMeta):
    __name__ = 'stock.shipment.internal'

    @classmethod
    def __setup__(cls):
        super(ShipmentInternal, cls).__setup__()
        cls.moves.add_remove = [
            ('shipment', '=', None),
            ('state', 'in', ('draft', 'assigned')),
            ('from_location', '=', Eval('from_location')),
            ('to_location', '=', Eval('to_location')),
            ]
        for fname in ('from_location', 'to_location'):
            if fname not in cls.moves.depends:
                cls.moves.depends.append(fname)


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
        t = cls.__table__()
        cls._sql_constraints += [
            ('check_from_to_warehouses',
                Check(t, t.from_warehouse != t.to_warehouse),
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
        return datetime.now()

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
            if not request.lines:
                raise UserError(gettext(
                    'stock_supply_request.msg_lines_required_confirmed',
                    request=request.rec_name))
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
        if not config.supply_request_sequence:
            raise UserError(gettext(
                    'stock_supply_request.msg_missing_supply_request_sequence'))
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

    @classmethod
    def delete(cls, requests):
        for request in requests:
            if request.state != 'draft':
                raise UserError(gettext(
                        'stock_supply_request.msg_deletion_not_allowed',
                        request=request.rec_name))
        super(SupplyRequest, cls).delete(requests)


class SupplyRequestLine(ModelSQL, ModelView):
    'Supply Request Line'
    __name__ = 'stock.supply_request.line'

    request = fields.Many2One('stock.supply_request', 'Request', required=True,
        ondelete='CASCADE')
    company = fields.Function(fields.Many2One('company.company', 'Company'),
        'get_company', searcher='search_company')
    product = fields.Many2One('product.product', 'Product', domain=[
            ('type', '!=', 'service'),
            ], required=True)
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
                ('parent', 'child_of', [Eval('_parent_request', {}).get(
                        'to_warehouse', 0)]),
                ()),
            ])
    delivery_date = fields.Date("Delivery Date", required=True)
    move = fields.Many2One('stock.move', 'Reserve', readonly=True, domain=[
            ('product', '=', Eval('product')),
            ],
        states={
            'required': Equal(Eval('_parent_request.state'), 'confirmed'),
            }, depends=['product'])
    supply_state = fields.Function(fields.Selection([
                ('pending', 'Pending'),
                ('in_progress', 'In Progress'),
                ('done', 'Done'),
                ('cancel', 'Canceled'),
                ], 'Supply State'),
        'get_supply_state')

    @staticmethod
    def default_delivery_date():
        Date = Pool().get('ir.date')
        return Date.today() + timedelta(days=2)

    def get_company(self, name):
        return self.request and self.request.company.id

    @classmethod
    def search_company(cls, name, clause):
        return [('request.%s' % name,) + tuple(clause[1:])]

    @fields.depends('product', 'unit', 'unit_digits')
    def on_change_product(self):
        if self.product:
            self.unit = self.product.default_uom
            self.unit_digits = self.product.default_uom.digits

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
        if not self.move or self.move.state == 'draft':
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
