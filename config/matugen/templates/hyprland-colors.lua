-- Generado por matugen, no editar a mano
return {
<* for name, value in colors *>
    {{name}} = "rgba({{value.default.hex_stripped}}ff)",
<* endfor *>
}
