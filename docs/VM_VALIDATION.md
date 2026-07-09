# VM Validation — Checklist de validación de `bcs` en Ubuntu 24.04

Checklist estructurada para validar el funcionamiento de `bcs` en una máquina virtual recién instalada.

**Instrucciones:** por cada prueba, ejecutar el comando, comparar con el resultado esperado, marcar PASS o FAIL y anotar cualquier incidencia en Notas.

---

## Prerrequisitos

- [ ] VM creada según [VM_FIRST_BOOT.md](VM_FIRST_BOOT.md)
- [ ] `bcs` instalado según [VM_INSTALLATION.md](VM_INSTALLATION.md)
- [ ] Venv activado (`source .venv/bin/activate`)
- [ ] Directorio actual = `batoi-classroom-suite/cli/`

---

## TC-01: `bcs --help`

| Campo | Valor |
|---|---|
| **Objetivo** | Verificar que el árbol de comandos se muestra correctamente |
| **Comando** | `bcs --help` |
| **Resultado esperado** | Muestra uso, opciones globales y lista de 11 comandos: `doctor`, `inventory`, `validate`, `build`, `install`, `deploy`, `backup`, `restore`, `update`, `version`, `config` |
| **Resultado real** | |
| **PASS/FAIL** | |
| **Notas** | |

---

## TC-02: `bcs` (sin argumentos)

| Campo | Valor |
|---|---|
| **Objetivo** | Verificar que el comando sin argumentos muestra ayuda |
| **Comando** | `bcs` |
| **Resultado esperado** | Misma salida que `bcs --help`, exit code 0 |
| **Resultado real** | |
| **PASS/FAIL** | |
| **Notas** | |

---

## TC-03: `bcs version` (texto)

| Campo | Valor |
|---|---|
| **Objetivo** | Verificar que la versión se muestra en texto plano |
| **Comando** | `bcs version` |
| **Resultado esperado** | Muestra `version`, `commit`, `buildDate`, `supportedConfigApiVersions` en texto legible |
| **Resultado real** | |
| **PASS/FAIL** | |
| **Notas** | |

---

## TC-04: `bcs version --output json`

| Campo | Valor |
|---|---|
| **Objetivo** | Verificar que la versión se muestra en JSON válido |
| **Comando** | `bcs version --output json` |
| **Resultado esperado** | JSON con campos: `schemaVersion`, `version`, `commit`, `buildDate`, `supportedConfigApiVersions` |
| **Resultado real** | |
| **PASS/FAIL** | |
| **Notas** | |

---

## TC-05: `bcs version --output yaml`

| Campo | Valor |
|---|---|
| **Objetivo** | Verificar que la versión se muestra en YAML válido |
| **Comando** | `bcs version --output yaml` |
| **Resultado esperado** | YAML con los mismos campos que el JSON |
| **Resultado real** | |
| **PASS/FAIL** | |
| **Notas** | |

---

## TC-06: `bcs --version` (flag global)

| Campo | Valor |
|---|---|
| **Objetivo** | Verificar que `--version` es atajo para `bcs version` |
| **Comando** | `bcs --version` |
| **Resultado esperado** | Misma salida que `bcs version` |
| **Resultado real** | |
| **PASS/FAIL** | |
| **Notas** | |

---

## TC-07: `bcs validate` (config ejemplo)

| Campo | Valor |
|---|---|
| **Objetivo** | Validar que el config de ejemplo pasa la validación |
| **Comando** | `bcs validate ../config/examples/default.yaml` |
| **Resultado esperado** | Exit code 0, muestra `Valid: true` o equivalente |
| **Resultado real** | |
| **PASS/FAIL** | |
| **Notas** | |

---

## TC-08: `bcs validate` (config inexistente)

| Campo | Valor |
|---|---|
| **Objetivo** | Verificar que un archivo inexistente da error |
| **Comando** | `bcs validate no-existe.yaml` |
| **Resultado esperado** | Exit code != 0, mensaje de error claro ("file not found" o similar) |
| **Resultado real** | |
| **PASS/FAIL** | |
| **Notas** | |

---

## TC-09: `bcs validate --help`

| Campo | Valor |
|---|---|
| **Objetivo** | Verificar que el subcomando tiene ayuda |
| **Comando** | `bcs validate --help` |
| **Resultado esperado** | Muestra uso del subcomando validate |
| **Resultado real** | |
| **PASS/FAIL** | |
| **Notas** | |

---

## TC-10: `bcs inventory` (texto)

| Campo | Valor |
|---|---|
| **Objetivo** | Verificar que el inventario se muestra en texto |
| **Comando** | `bcs inventory` |
| **Resultado esperado** | Muestra secciones: identity, firmware, operatingSystem, cpu, memory, storage, network, efiSystemPartition, usbStorage, tooling |
| **Resultado real** | |
| **PASS/FAIL** | |
| **Notas** | |

---

## TC-11: `bcs inventory --output json`

| Campo | Valor |
|---|---|
| **Objetivo** | Verificar que el inventario se muestra en JSON válido |
| **Comando** | `bcs inventory --output json` |
| **Resultado esperado** | JSON válido con `schemaVersion: "bcs-inventory/v1alpha1"` |
| **Resultado real** | |
| **PASS/FAIL** | |
| **Notas** | |

---

## TC-12: `bcs inventory --output yaml`

| Campo | Valor |
|---|---|
| **Objetivo** | Verificar que el inventario se muestra en YAML válido |
| **Comando** | `bcs inventory --output yaml` |
| **Resultado esperado** | YAML válido parseable por `python3 -c "import yaml; yaml.safe_load(open('/dev/stdin'))"` |
| **Resultado real** | |
| **PASS/FAIL** | |
| **Notas** | |

---

## TC-13: JSON del inventario es parseable

| Campo | Valor |
|---|---|
| **Objetivo** | Verificar que el JSON no está truncado ni corrupto |
| **Comando** | `bcs inventory --output json | python3 -m json.tool > /dev/null` |
| **Resultado esperado** | Exit code 0, sin errores |
| **Resultado real** | |
| **PASS/FAIL** | |
| **Notas** | |

---

## TC-14: `bcs doctor` (completo)

| Campo | Valor |
|---|---|
| **Objetivo** | Verificar que el doctor ejecuta todas las comprobaciones |
| **Comando** | `bcs doctor` |
| **Resultado esperado** | Muestra checks: firmware, storage, network, tooling, config, permissions, esp, usb-storage. Cada check muestra [OK], [WARN] o [FAIL]. No se cuelga. |
| **Resultado real** | |
| **PASS/FAIL** | |
| **Notas** | |

---

## TC-15: `bcs doctor --check` (filtro)

| Campo | Valor |
|---|---|
| **Objetivo** | Verificar que se puede ejecutar un solo check |
| **Comando** | `bcs doctor --check firmware` |
| **Resultado esperado** | Muestra solo el check `firmware`, no el resto |
| **Resultado real** | |
| **PASS/FAIL** | |
| **Notas** | |

---

## TC-16: `bcs doctor --output json`

| Campo | Valor |
|---|---|
| **Objetivo** | Verificar que el doctor produce JSON |
| **Comando** | `bcs doctor --output json` |
| **Resultado esperado** | JSON con resultados por check |
| **Resultado real** | |
| **PASS/FAIL** | |
| **Notas** | |

---

## TC-17: `bcs doctor` como usuario normal

| Campo | Valor |
|---|---|
| **Objetivo** | Verificar que el doctor funciona sin privilegios |
| **Comando** | `bcs doctor` (ejecutado como `tech`, SIN `sudo`) |
| **Resultado esperado** | Todos los checks se ejecutan. Algunos pueden fallar si requieren permisos, pero no debe crashear. |
| **Resultado real** | |
| **PASS/FAIL** | |
| **Notas** | |

---

## TC-18: `bcs doctor` con sudo

| Campo | Valor |
|---|---|
| **Objetivo** | Verificar que el doctor funciona con sudo (sin venv) |
| **Comando** | `sudo bcs doctor` (ejecutado desde fuera del venv) |
| **Resultado esperado** | Puede fallar si `bcs` no está en PATH del superusuario. Anotar comportamiento observado. |
| **Resultado real** | |
| **PASS/FAIL** | |
| **Notas** | |

---

## TC-19: Comando desconocido

| Campo | Valor |
|---|---|
| **Objetivo** | Verificar manejo de errores en comandos inválidos |
| **Comando** | `bcs comando-inventado` |
| **Resultado esperado** | Exit code 8, mensaje "unknown command" |
| **Resultado real** | |
| **PASS/FAIL** | |
| **Notas** | |

---

## TC-20: Verbosidad (`-v`)

| Campo | Valor |
|---|---|
| **Objetivo** | Verificar que `-v` produce logs en stderr |
| **Comando** | `bcs -v inventory 2>/dev/null` (descarta stderr, solo stdout) y `bcs -v inventory 2>&1 1>/dev/null` (solo stderr) |
| **Resultado esperado** | stdout contiene el inventario; stderr contiene mensajes de depuración |
| **Resultado real** | |
| **PASS/FAIL** | |
| **Notas** | |

---

## TC-21: Opción `--output json` con `bcs doctor`

| Campo | Valor |
|---|---|
| **Objetivo** | Verificar JSON de doctor tiene schemaVersion |
| **Comando** | `bcs doctor --output json` |
| **Resultado esperado** | JSON con `schemaVersion: "bcs-cli/v1alpha1"` |
| **Resultado real** | |
| **PASS/FAIL** | |
| **Notas** | |

---

## TC-22: Stubs (comandos no implementados)

| Campo | Valor |
|---|---|
| **Objetivo** | Verificar que los stubs informan "no implementado" |
| **Comando** | `bcs build` |
| **Resultado esperado** | Mensaje "not implemented in this phase" y exit code != 0 |
| **Resultado real** | |
| **PASS/FAIL** | |
| **Notas** | |

Repetir para: `install`, `deploy`, `backup`, `restore`, `update`, `config`

---

## TC-23: Rendimiento — `bcs doctor`

| Campo | Valor |
|---|---|
| **Objetivo** | El doctor debe completarse en menos de 5 segundos |
| **Comando** | `time bcs doctor` |
| **Resultado esperado** | `real` < 5 segundos |
| **Resultado real** | |
| **PASS/FAIL** | |
| **Notas** | |

---

## TC-24: Rendimiento — `bcs inventory`

| Campo | Valor |
|---|---|
| **Objetivo** | El inventario debe completarse en menos de 5 segundos |
| **Comando** | `time bcs inventory` |
| **Resultado esperado** | `real` < 5 segundos |
| **Resultado real** | |
| **PASS/FAIL** | |
| **Notas** | |

---

## TC-25: Salida a archivo

| Campo | Valor |
|---|---|
| **Objetivo** | Verificar que se puede redirigir la salida a un archivo |
| **Comando** | `bcs inventory --output json > /tmp/inventory.json && cat /tmp/inventory.json | python3 -m json.tool > /dev/null` |
| **Resultado esperado** | Archivo JSON válido y parseable |
| **Resultado real** | |
| **PASS/FAIL** | |
| **Notas** | |

---

## TC-26: Múltiples ejecuciones

| Campo | Valor |
|---|---|
| **Objetivo** | Verificar que no hay efectos secundarios entre ejecuciones |
| **Comando** | `bcs doctor; bcs inventory; bcs validate ../config/examples/default.yaml` (tres comandos seguidos) |
| **Resultado esperado** | Los tres comandos se ejecutan correctamente, el segundo no falla por algo que hizo el primero |
| **Resultado real** | |
| **PASS/FAIL** | |
| **Notas** | |

---

## TC-27: Ayuda de stubs

| Campo | Valor |
|---|---|
| **Objetivo** | Verificar que los stubs muestran ayuda con `--help` |
| **Comando** | `bcs build --help` |
| **Resultado esperado** | Muestra el uso del comando aunque no esté implementado |
| **Resultado real** | |
| **PASS/FAIL** | |
| **Notas** | |

---

## Resumen de validación

| Fecha | Validador | Versión `bcs` | PASS total | FAIL total | % Éxito |
|---|---|---|---|---|---|
| | | | | | |

---

## Criterios de aceptación

| Criterio | Para aprobar |
|---|---|
| MVP funcional | TC-01 al TC-12: todos PASS |
| Robustez | TC-08, TC-19: comportamiento correcto ante errores |
| Rendimiento | TC-23, TC-24: < 5 segundos cada uno |
| Formato datos | TC-04, TC-11, TC-13: JSON válido y parseable |

---

## Siguiente paso

Si encuentras algún fallo, usar [VM_BUG_REPORT_TEMPLATE.md](VM_BUG_REPORT_TEMPLATE.md) para reportarlo.

Registrar todas las pruebas en [VM_TEST_LOG.md](VM_TEST_LOG.md).
