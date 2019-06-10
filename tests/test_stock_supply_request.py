#!/usr/bin/env python
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import unittest
import trytond.tests.test_tryton
from decimal import Decimal
from trytond.pool import Pool
from trytond.tests.test_tryton import ModuleTestCase, with_transaction

from trytond.modules.company.tests import create_company, set_company


class TestCase(ModuleTestCase):
    'Test module'
    module = 'stock_supply_request'

    @with_transaction()
    def test0010moves(self):
        'Test moves'
        pool = Pool()
        Configuration = pool.get('stock.configuration')
        Sequence = pool.get('ir.sequence')
        Template = pool.get('product.template')
        Product = pool.get('product.product')
        Uom = pool.get('product.uom')
        Location = pool.get('stock.location')
        Request = pool.get('stock.supply_request')
        RequestLine = pool.get('stock.supply_request.line')

        # Create Company
        company = create_company()
        with set_company(company):
            configuration, = Configuration.search([])
            supply_sequence, = Sequence.search([
                    ('code', '=', 'stock.supply_request'),
                    ])
            kg, = Uom.search([('name', '=', 'Kilogram')])
            warehouse, = Location.search([('code', '=', 'WH')])

            configuration.supply_request_sequence = supply_sequence
            configuration.default_request_from_warehouse = warehouse
            configuration.save()

            template, = Template.create([{
                        'name': 'Test Supply Request',
                        'type': 'goods',
                        'list_price': Decimal(1),
                        'cost_price_method': 'fixed',
                        'default_uom': kg.id,
                        }])
            product, = Product.create([{
                        'template': template.id,
                        }])

            storage2 = Location(type='storage', name='Warehouse2 STO',
                code='STO2')
            production_loc = Location(type='production', name='Location',
                code='Location')

            storage2.save()
            warehouse2 = Location(type='warehouse',
                name='Warehouse2',
                code='WH2',
                input_location=storage2,
                output_location=storage2,
                production_location=production_loc,
                storage_location=storage2)
            warehouse2.save()
            storage2.parent = warehouse2.id
            storage2.save()

            locations = Location.create([{
                        'code': 'LOC1',
                        'name': 'LOC1',
                        'type': 'storage',
                        'parent': storage2.id,
                        }, {
                        'code': 'LOC2',
                        'name': 'LOC2',
                        'type': 'storage',
                        'parent': storage2.id,
                        }])

            request = Request(company=company.id,
                from_warehouse=warehouse,
                to_warehouse=warehouse2,
                lines=[])
            for qty, to_location in ((2.0, locations[0]), (4.0, locations[1])):
                request_line = RequestLine()
                request.lines = (request_line,)
                request_line.product = product
                request_line.quantity = qty
                request_line.to_location = to_location
            request.save()

            Request.confirm([request])

            for line in request.lines:
                self.assertEqual(bool(line.move), True)
                self.assertEqual(line.product, line.move.product)
                self.assertEqual(line.quantity, line.move.quantity)
                self.assertEqual(request.from_warehouse.storage_location,
                    line.move.from_location)
                self.assertEqual(line.to_location, line.move.to_location)


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCase))
    return suite
