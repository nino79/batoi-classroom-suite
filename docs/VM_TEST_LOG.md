# Test Log — Validación MVP en VirtualBox

Diario de pruebas. Cada entrada documenta una sesión completa de validación.

---

## Formato de entrada

Cada sesión debe incluir:

```
## YYYY-MM-DD — Sesión N

**Validador:**
**Duración:**
**Snapshots usados:** (ej: desde "02-bcs-installed")
**Hoja de validación:** VM_VALIDATION.md (TC-01 a TC-XX)

### Resultados

| TC-id | PASS/FAIL | Notas |
|---|---|---|
| TC-01 | | |
| TC-02 | | |
| ... | | |

### Bugs encontrados

| ID | TC | Descripción | Prioridad |
|---|---|---|---|
| BUG-01 | TC-07 | ... | Alta |

### Incidencias técnicas

(Problemas de VM, red, snapshots, etc.)

### Observaciones

(Cualquier nota sobre el proceso de validación)
```

---

## Entradas

<!--

### Ejemplo de uso:

## 2026-07-10 — Sesión 1

**Validador:** Ana
**Duración:** 45 min
**Snapshots usados:** desde "01-fresh-ubuntu-2404"
**Hoja de validación:** VM_VALIDATION.md (TC-01 a TC-14)

### Resultados

| TC-id | PASS/FAIL | Notas |
|---|---|---|
| TC-01 | PASS | |
| TC-02 | PASS | |
| TC-03 | FAIL | bcs version no muestra commit (BUG-01) |

### Bugs encontrados

| ID | TC | Descripción | Prioridad |
|---|---|---|---|
| BUG-01 | TC-03 | bcs version muestra commit vacío | Alta |

### Observaciones

La VM responde bien. El fallo de TC-03 parece ser del entorno, no del código.
-->

---

## Histórico de sesiones

| Sesión | Fecha | Validador | PASS | FAIL | Total | % |
|---|---|---|---|---|---|---|
| | | | | | | |
