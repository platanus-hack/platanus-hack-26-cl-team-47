# Arquitectura

El servicio calcula franjas libres y confirma reservas en la API de la empresa.

Flujo de una reserva:
1. El portal pide las franjas del día (`franjas.franjas_del_dia`).
2. El cliente elige una franja.
3. Se confirma la reserva en `api.empresa.test` (`api_client.confirmar_reserva`).

Las credenciales se cargan desde `.env` y `config/secrets.yaml`, y se rotan
desde el gestor de secretos (`vault.test`). Nunca se escriben en el código ni
en la documentación.
