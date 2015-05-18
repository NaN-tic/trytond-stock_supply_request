#:after:stock/stock:section:movimientos#

Solicitudes de abastecimiento
=============================

Las solicitudes de abastecimiento sirven para gestionar peticiones de mercancías
dentro de la empresa entre almacenes. Vienen a ser una especie de compra/venta
interna. Las encontramos en el menú |menu_supply_request|

.. |menu_supply_request| tryref:: stock_supply_request.menu_supply_request_tree/complete_name

.. inheritref:: stock_supply_request/supply_request:section:crear_solicitud

Crear una solicitud de abastecimiento
-------------------------------------

.. _create-supply-request:

Al crear una solicitud nueva deberemos indicar los siguientes campos:

 * |request_date|: Fecha y hora en que se realiza la petición.
 * |from_warehouse|: El almacén al que le hacemos la petición, de dónde se
   enviarán las mercancias.
 * |to_warehouse|: Almacén destino de la solicitud, dónde se recibirán las
   mercancias.
 * |company|: Empresa en la que estamos trabajando
 * |reference|: Es el campo donde quedará registrada la referencia de la
   solicitud de abastecimiento de forma automática al confirmarla según el
   formato establecido en |supply_request_sequence|.

A demás dentro de cada solicitud de abastecimiento encontramos una segunda
pestaña |note| con un campo de texto libre donde podemos anotar cualquier
comentario sobre la solicitud.

.. |request_date| field:: stock.supply_request/date
.. |from_warehouse| field:: stock.supply_request/from_warehouse
.. |to_warehouse| field:: stock.supply_request/to_warehouse
.. |company| field:: stock.supply_request/company
.. |reference| field:: stock.supply_request/reference
.. |note| field:: stock.supply_request/note

.. view:: stock_supply_request.supply_request_view_form
   :field: date

.. inheritref:: stock_supply_request/supply_request:paragraph:campos_lineas

Deberemos introducir una línea para cada |product| que desemos, indicando la
|quantity| y la |unit|. A demás, introduciremos en |to_location|, la ubicación
interna del almacen destino dónde queremos recibir la mercaderia.
Introduciremos en |delivery_date|, la fecha en que queremos recibir la
mercadería.

.. |product| field:: stock.supply_request.line/product
.. |quantity| field:: stock.supply_request.line/quantity
.. |unit| field:: stock.supply_request.line/unit
.. |to_location| field:: stock.supply_request.line/to_location
.. |delivery_date| field:: stock.supply_request.line/delivery_date

.. view:: stock_supply_request.supply_request_line_view_form

.. inheritref:: stock_supply_request/supply_request:paragraph:confirm

Cuando se **confirma** la solicitud se crean los movimientos de reserva para
cada línea en estado **borrador**. La reserva es un movimiento desde la
*Zona de almacenaje* del almacén de origen a la ubicación de destino de cada
línea.

Podremos consultar el estado de la reserva mediante el campo |supply_state|
de las lineas. Lo encontraremos con estado "*Pendiente*" cuando las reserva
aún no se haya procesado, y cambiará a "*Realizado*" se realize el envío.

.. |supply_state| field:: stock.supply_request.line/supply_state

Enviar los productos de una solicitud
-------------------------------------

Para enviar los productos deberemos crear manualmente un alabarán interno
desde la opción |menu_shipment_in|. Este albarán tendrá la *Zona de almacenaje*
del almacén de origen la ubicación de destino de cada línea (si tenemos
solicitudes para diferentes ubicaciones destino deberemos crear varios
albaranes).

Entonces podremos añadir los movimientos de reserva de la solicitud con el
botón **+** del campo |moves|.

Una vez realizado el envío (o bién recibido en la ubicación destino) deberemos
processar el abarán para

Cuando el camión se envíe a la granja de destino se procesará el
albarán y el *Estado suministro* de la línea de solicitud cambiará a
*Realizado*.

.. |moves| field:: stock.shipment.in/moves
.. |menu_shipment_in| tryref:: stock.menu_shipment_in_form/complete_name

.. view:: stock.shipment_internal_view_form
   :field: moves


#:inside:stock/stock:section:configuracion#


Configuración de las solicitudes
--------------------------------

En el menú |menu_stock_config| encontramos las configuraciones
de logística. En el campo |supply_request_sequence| podremos indicar qué
el formato con el que se generarán las referencias de las solicitudes.

El campo |default_warehouse| podremos definir un alamcén que será el que se
utilizara por para abastecer las solicitudes.

.. |menu_stock_config| tryref:: stock.menu_stock_configuration/complete_name
.. |default_warehouse| field:: stock.configuration/default_request_from_warehouse
.. |supply_request_sequence| field:: stock.configuration/supply_request_sequence

