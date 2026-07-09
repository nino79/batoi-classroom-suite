# VM Installation — Instalar `bcs` en Ubuntu 24.04

Protocolo exacto de instalación. Cada comando debe copiarse y pegarse textualmente.

**Requisito:** Haber completado [VM_FIRST_BOOT.md](VM_FIRST_BOOT.md). La VM debe estar encendida y con sesión iniciada como `tech`.

---

## 1. Abrir terminal

```bash
# Si estás en la interfaz gráfica (no SSH):
# Pulsa Ctrl+Alt+T o busca "Terminal" en el menú

# Si estás por SSH:
ssh tech@<IP_DE_LA_VM>
```

---

## 2. Actualizar sistema

```bash
sudo apt update
```

Si pide contraseña, escribir la contraseña del usuario `tech`.

---

## 3. Instalar dependencias

```bash
sudo apt install -y git python3-venv
```

Esto instala:
- `git` — para clonar el repositorio
- `python3-venv` — para crear el entorno virtual

Tiempo estimado: 30-60 segundos.

---

## 4. Clonar el repositorio

```bash
git clone https://github.com/nino79/batoi-classroom-suite.git
```

Esto crea una carpeta `batoi-classroom-suite` en el directorio actual (`/home/tech/`).

---

## 5. Entrar al directorio

```bash
cd batoi-classroom-suite/cli
```

---

## 6. Crear entorno virtual

```bash
python3 -m venv .venv
```

Explicación: esto crea una carpeta oculta `.venv/` con su propio Python y pip, aislado del sistema. Siempre hay que trabajar dentro de este entorno.

---

## 7. Activar el entorno virtual

```bash
source .venv/bin/activate
```

Después de ejecutar esto, el prompt cambia para mostrar `(.venv)` al inicio:

```
(.venv) tech@bcs-validation:~/batoi-classroom-suite/cli$
```

Si no ves `(.venv)` al inicio, la activación no funcionó.

---

## 8. Instalar `bcs`

```bash
pip install -e ".[dev]"
```

Esto instala:
- El paquete `bcs` en modo editable (`-e`): cualquier cambio en el código fuente se refleja al instante
- Las dependencias de ejecución: Typer, Rich, Pydantic, PyYAML
- Las dependencias de desarrollo: Ruff, mypy, pytest, pytest-cov

Tiempo estimado: 30-60 segundos.

---

## 9. Verificar instalación

```bash
bcs --help
```

Debería mostrar el árbol de comandos completo.

```bash
bcs version
```

Debería mostrar la versión, commit y fecha de compilación.

---

## 10. Snapshot post-instalación

Una vez confirmado que `bcs --help` funciona, crear un segundo snapshot:

```bash
# Desde el HOST (NO desde la VM):
VBoxManage snapshot "bcs-validation" take "02-bcs-installed"
```

---

## Solución de problemas

| Problema | Causa | Solución |
|---|---|---|
| `sudo: apt: command not found` | No es Ubuntu | Verificar que la ISO es Ubuntu 24.04 |
| `git: command not found` | No se instaló git | `sudo apt install -y git` |
| `python3: command not found` | No hay Python 3 | `sudo apt install -y python3` |
| `ensurepip is not available` | Falta `python3-venv` | `sudo apt install -y python3-venv` |
| `bcs: command not found` | Venv no activado | `source .venv/bin/activate` |
| `externally-managed-environment` | pip fuera del venv | Crear y activar el venv primero |
| Permiso denegado al clonar | Sin git config | No hace falta — es clon anónimo (HTTPS) |

---

## Siguiente paso

Ir a [VM_VALIDATION.md](VM_VALIDATION.md) para ejecutar las pruebas de validación.
