#!/bin/sh
# Deja en el sitio la escena con terminales, el tablero de pruebas y el informe técnico.
#
#   sh demo/alternativas/03-enjambre-juanpedro/publicar.sh [destino]
#
# El sitio publica demo/viz (vercel.json). Este script copia ahí, en demo/viz/escena/, lo que la
# página necesita para funcionar sin servidor: los HTML, CSS y JS de esta carpeta, sus datos, las
# grabaciones y el PDF del informe. vercel.json lo corre en el paso de instalación, antes del build.
# No copia Python, tests ni documentos. demo/viz/escena/ no se versiona (.gitignore).
set -e
aqui=$(cd "$(dirname "$0")" && pwd)
raiz=$(cd "$aqui/../../.." && pwd)
destino=${1:-"$raiz/demo/viz/escena"}

mkdir -p "$destino/grabaciones"
for tipo in html css js json; do
  cp "$aqui"/*."$tipo" "$destino/"
done
cp "$aqui"/grabaciones/* "$destino/grabaciones/"
cp "$raiz/docs/informe/informe.pdf" "$destino/informe.pdf"
# La escena usa el logo de la demo oficial, que vive en otra carpeta: la copia lo lleva consigo.
cp "$raiz/demo/viz/logo.png" "$destino/logo.png"
sed 's#\.\./\.\./viz/logo\.png#logo.png#g' "$aqui/enjambre.html" > "$destino/enjambre.html"
if grep -q '\.\./' "$destino"/*.html; then
  echo "publicar.sh: una página de la copia apunta fuera de su carpeta" >&2
  exit 1
fi
echo "escena publicada en $destino"
