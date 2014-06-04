# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .supply_request import *


def register():
    Pool.register(
        Configuration,
        ConfigurationCompany,
        Move,
        ShipmentInternal,
        SupplyRequest,
        SupplyRequestLine,
        module='stock_supply_request', type_='model')
