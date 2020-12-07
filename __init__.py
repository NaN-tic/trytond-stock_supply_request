# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import supply_request


def register():
    Pool.register(
        supply_request.Configuration,
        supply_request.ConfigurationCompany,
        supply_request.Move,
        supply_request.ShipmentInternal,
        supply_request.SupplyRequest,
        supply_request.SupplyRequestLine,
        module='stock_supply_request', type_='model')
