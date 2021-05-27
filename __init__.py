# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import configuration
from . import supply_request


def register():
    Pool.register(
        configuration.Configuration,
        configuration.ConfigurationSequence,
        configuration.ConfigurationLocation,
        supply_request.Move,
        supply_request.ShipmentInternal,
        supply_request.SupplyRequest,
        supply_request.SupplyRequestLine,
        module='stock_supply_request', type_='model')
