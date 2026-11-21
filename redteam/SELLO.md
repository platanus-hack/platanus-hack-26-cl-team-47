# Sello del set de prueba (issue #120, paso 11)

**Sellado hasta el congelamiento de H20; lo abre el líder.**

El set de prueba y su generador viven en la rama `11-set-sellado` y **no entran a `main`**
hasta H20. Este archivo solo publica su sello para que, al abrirlo, se compruebe que no cambió.

- **Sello (sha256):** `18dda3af7ee2b088515fb80f9104dc6516b83a8df7d160e18f08fab4efaa18a9`
- **Commit sellado:** `77457d90aefe8ca2dfb5a3134450bc4e54afe1e7` (rama `11-set-sellado`)
- **Fecha y hora:** 2026-11-21 07:10 -03 (sábado, ~H8)

## Cantidades por familia

| Familia | Sesiones |
|---|---|
| A5  | 30 |
| A7  | 30 (grupos) |
| A9  | 30 |
| A10 | 30 |
| A12 | 30 |
| A13 | 30 |
| B3  | 30 |
| B4  | 30 |
| B5  | 30 |

## Cómo verificar el sello

Desde la raíz del repo, con la rama `11-set-sellado` extraída:

```
{ find redteam/test -type f; echo redteam/sealed.py; } | LC_ALL=C sort \
  | tr '\n' '\0' | xargs -0 shasum -a 256 | LC_ALL=C sort -k2 | shasum -a 256
```

El hash resultante debe coincidir con el sello de arriba. (El sello es el sha256 de la
concatenación, en orden alfabético de ruta, de las líneas `<sha256>  <ruta relativa>` de todos
los archivos bajo `redteam/test/` más `redteam/sealed.py`.) Regenerar con
`python -m redteam.sealed --seed 2 --out redteam/test` produce los mismos archivos byte a byte.

## Apertura

Abierto el sábado 21 de noviembre de 2026 a las 09:40, por decisión del líder de adelantar el congelamiento. La configuración quedó congelada antes (commit `3f26307`, etiqueta `congelamiento`). El sello se recalculó sobre `main` después de traer la rama y coincide con el de arriba. La evaluación final se corrió una sola vez, en el commit `cd14e9e`; resultados en `results/test/`.
