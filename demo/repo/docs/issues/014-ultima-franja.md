# #14 La última franja del día no aparece

Con cierre a las 18:00 y franjas de 30 minutos, la franja de las 17:30 nunca
se ofrece.

Esperado: la última franja ofrecida es la que termina justo al cierre.

El test `tests/test_franjas.py::test_incluye_ultima_franja` lo reproduce.
