# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, Id

__all__ = ['Configuration', 'ConfigurationSequence', 'ConfigurationLocation']

supply_request_sequence = fields.Many2One(
    'ir.sequence', "Supply Request Sequence", required=True,
    domain=[
        ('company', 'in',
            [Eval('context', {}).get('company', -1), None]),
        ('sequence_type', '=', Id('stock_supply_request',
                'sequence_type_supply_request')),
        ])
request_from_warehouse = fields.Many2One(
    'stock.location', "Request From Warehouse", required=True,
    domain=[
        ('type', '=', 'warehouse'),
        ])

def default_func(field_name):
    @classmethod
    def default(cls, **pattern):
        return getattr(
            cls.multivalue_model(field_name),
            'default_%s' % field_name, lambda: None)()
    return default

def default_sequence(name):
    @classmethod
    def default(cls):
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        try:
            return ModelData.get_id('stock_supply_request', name)
        except KeyError:
            return None
    return default


class Configuration(metaclass=PoolMeta):
    __name__ = 'stock.configuration'
    supply_request_sequence = fields.MultiValue(supply_request_sequence)
    request_from_warehouse = fields.MultiValue(request_from_warehouse)

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field == 'supply_request_sequence':
            return pool.get('stock.configuration.sequence')
        if field == 'request_from_warehouse':
            return pool.get('stock.configuration.location')
        return super(Configuration, cls).multivalue_model(field)

    default_supply_request_sequence = default_func('supply_request_sequence')


class ConfigurationSequence(metaclass=PoolMeta):
    __name__ = 'stock.configuration.sequence'
    supply_request_sequence = supply_request_sequence

    default_supply_request_sequence = default_sequence('sequence_supply_request')


class ConfigurationLocation(metaclass=PoolMeta):
    __name__ = 'stock.configuration.location'
    request_from_warehouse = request_from_warehouse
