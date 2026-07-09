# Bug Report — Validación MVP en VirtualBox

Usar esta plantilla para reportar cualquier fallo encontrado durante la validación en VM.

---

## Metadatos

| Campo | Valor |
|---|---|
| **ID** | `BUG-` (rellenar número correlativo) |
| **Fecha** | |
| **Validador** | |
| **Versión `bcs`** | `bcs version --output json` |
| **Commit** | `git log --oneline -1` |
| **TC asociado** | (ej: TC-07) |

---

## Entorno

### Hardware (Host)

| Campo | Valor |
|---|---|
| Modelo | |
| CPU | |
| RAM | |
| SO host | |

### VirtualBox

| Campo | Valor |
|---|---|
| Versión | `VBoxManage --version` |
| Extension Pack | Sí / No |
| RAM asignada | |
| CPUs asignadas | |
| EFI activado | Sí / No |
| Controlador | NVMe / SATA |

### Ubuntu (VM)

| Campo | Valor |
|---|---|
| Versión | `lsb_release -a` |
| Kernel | `uname -a` |
| Python | `python3 --version` |
| Paquetes instalados | `apt list --installed 2>/dev/null | grep -E 'python3-venv|git'` |

---

## Descripción del fallo

### Comando ejecutado

```
(p eg: bcs validate ../config/examples/default.yaml)
```

### Salida obtenida

```
(p eg: pegar aquí la salida completa, stdout + stderr)
```

### Salida esperada

```
(p eg: pegar aquí lo que debería haber salido)
```

### Código de salida

| Obtenido | Esperado |
|---|---|
| `echo $?` → | |

---

## Logs

### Log de depuración

```bash
bcs -vv <comando> 2>/tmp/bcs-debug.log
```

Adjuntar `/tmp/bcs-debug.log`:

```
(pegar logs aquí o indicar "adjunto")
```

### Trace completo

```bash
bcs -vvv <comando> 2>/tmp/bcs-trace.log
```

Adjuntar `/tmp/bcs-trace.log` si es relevante:

```
(pegar logs aquí o indicar "adjunto")
```

---

## Capturas

- [ ] Captura de pantalla del error
- [ ] Captura de terminal con salida completa
- [ ] Captura de VirtualBox (si el fallo es de VM)

---

## Clasificación

| Prioridad | Definición | Marcar |
|---|---|---|
| 🔴 Crítico | `bcs` no arranca, crashea, o da datos incorrectos | |
| 🟠 Alto | `bcs` funciona pero un comando principal falla (doctor, inventory) | |
| 🟡 Medio | Funcionalidad secundaria afectada (formato output, stubs) | |
| 🔵 Bajo | Problema cosmético, error tipográfico, mejora menor | |

| Tipo | Marcar |
|---|---|
| Bug (regresión) | |
| Bug (nunca funcionó) | |
| Documentación incorrecta | |
| Error de validación (TC mal diseñado) | |
| Problema de entorno (VirtualBox/Ubuntu) | |

---

## Notas adicionales

```
(espacio para cualquier contexto adicional: pasos para reproducir,
si es intermitente, si ocurre siempre, etc.)
```

---

## Adjuntos

Listar archivos adjuntos:

- [ ] `/tmp/bcs-debug.log`
- [ ] `/tmp/bcs-trace.log`
- [ ] Captura de pantalla: `bug-XX-screenshot.png`
- [ ] Salida JSON: `bug-XX-output.json`
- [ ] Otro:
