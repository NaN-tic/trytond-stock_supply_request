#!/usr/bin/env python
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.

import sys
import os
DIR = os.path.abspath(os.path.normpath(os.path.join(__file__,
    '..', '..', '..', '..', '..', 'trytond')))
if os.path.isdir(DIR):
    sys.path.insert(0, os.path.dirname(DIR))

import unittest
import trytond.tests.test_tryton
from decimal import Decimal
from trytond.tests.test_tryton import POOL, DB_NAME, USER, CONTEXT, test_view,\
    test_depends
from trytond.transaction import Transaction


class TestCase(unittest.TestCase):
    '''
    Test module.
    '''

    def setUp(self):
        trytond.tests.test_tryton.install_module('stock_supply_request')
        self.configuration = POOL.get('stock.configuration')
        self.sequence = POOL.get('ir.sequence')
        self.template = POOL.get('product.template')
        self.product = POOL.get('product.product')
        self.uom = POOL.get('product.uom')
        self.location = POOL.get('stock.location')
        self.company = POOL.get('company.company')
        self.user = POOL.get('res.user')
        self.request = POOL.get('stock.supply_request')
        self.request_line = POOL.get('stock.supply_request.line')

    def test0005views(self):
        '''
        Test views.
        '''
        test_view('stock_supply_request')

    def test0006depends(self):
        '''
        Test depends.
        '''
        test_depends()

    def test0010moves(self):
        '''
        Test moves.
        '''
        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            company, = self.company.search([
                    ('rec_name', '=', 'Dunder Mifflin')])
            self.user.write([self.user(USER)], {
                'main_company': company.id,
                'company': company.id,
                })
            Transaction().context['company'] = company.id

            configuration, = self.configuration.search([])
            supply_sequence, = self.sequence.search([
                    ('code', '=', 'stock.supply_request'),
                    ])
            kg, = self.uom.search([('name', '=', 'Kilogram')])
            warehouse, = self.location.search([('code', '=', 'WH')])

            configuration.supply_request_sequence = supply_sequence
            configuration.default_request_from_warehouse = warehouse
            configuration.save()

            template, = self.template.create([{
                        'name': 'Test Supply Request',
                        'type': 'goods',
                        'list_price': Decimal(1),
                        'cost_price': Decimal(0),
                        'cost_price_method': 'fixed',
                        'default_uom': kg.id,
                        }])
            product, = self.product.create([{
                        'template': template.id,
                        }])

            storage2 = self.location(type='storage', name='Warehouse2 STO',
                code='STO2')
            production_loc = self.location(type='production', name='Location',
                code='Location')

            storage2.save()
            warehouse2 = self.location(type='warehouse',
                name='Warehouse2',
                code='WH2',
                input_location=storage2,
                output_location=storage2,
                production_location=production_loc,
                storage_location=storage2)
            warehouse2.save()
            storage2.parent = warehouse2.id
            storage2.save()

            locations = self.location.create([{
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

            request = self.request(company=company.id,
                from_warehouse=warehouse,
                to_warehouse=warehouse2,
                lines=[])
            for qty, to_location in ((2.0, locations[0]), (4.0, locations[1])):
                request_line = self.request_line()
                request.lines.append(request_line)
                request_line.product = product
                request_line.quantity = qty
                request_line.to_location = to_location
            request.save()

            self.request.confirm([request])

            for line in request.lines:
                self.assertEqual(bool(line.move), True)
                self.assertEqual(line.product, line.move.product)
                self.assertEqual(line.quantity, line.move.quantity)
                self.assertEqual(request.from_warehouse.storage_location,
                    line.move.from_location)
                self.assertEqual(line.to_location, line.move.to_location)


def suite():
    suite = trytond.tests.test_tryton.suite()
    from trytond.modules.company.tests import test_company
    for test in test_company.suite():
        if test not in suite:
            suite.addTest(test)
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCase))
    return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
