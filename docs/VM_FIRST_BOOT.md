# VM First Boot — Ubuntu 24.04 LTS

Protocolo para crear la máquina virtual desde cero, instalar Ubuntu 24.04 y dejar el sistema listo para instalar `bcs`.

---

## 1. Requisitos previos

| Recurso | Versión mínima |
|---|---|
| VirtualBox | 7.0+ con Extension Pack |
| ISO Ubuntu | `ubuntu-24.04-live-server-amd64.iso` |
| RAM disponible | 4 GB libres |
| Disco libre | 20 GB libres |

Descargar ISO: https://releases.ubuntu.com/24.04/

---

## 2. Crear máquina virtual

### 2.1. Parámetros

| Parámetro | Valor |
|---|---|
| Nombre | `bcs-validation` |
| Tipo | Linux |
| Versión | Ubuntu (64-bit) |
| RAM | 4096 MB |
| CPUs | 2 |
| Disco | 50 GB, Dinámicamente asignado |
| Controlador | NVMe (NO SATA) |
| EFI | ACTIVADO |
| Red | NAT |
| Audio | Desactivado |
| USB | Desactivado |
| Disquete | Desactivado |

### 2.2. Comandos VirtualBox (opcional)

```bash
# Crear VM
VBoxManage createvm --name "bcs-validation" --ostype Ubuntu24_64 --register

# RAM y CPU
VBoxManage modifyvm "bcs-validation" --memory 4096 --cpus 2

# EFI
VBoxManage modifyvm "bcs-validation" --firmware efi

# Controlador NVMe
VBoxManage storagectl "bcs-validation" --name "NVMe" --add nvme --controller NVMe

# Disco virtual
VBoxManage createvdi --filename "$HOME/VirtualBox VMs/bcs-validation/bcs-validation.vdi" --size 51200
VBoxManage storageattach "bcs-validation" --storagectl "NVMe" --port 0 --device 0 --type hdd \
  --medium "$HOME/VirtualBox VMs/bcs-validation/bcs-validation.vdi"

# Red NAT
VBoxManage modifyvm "bcs-validation" --nic1 nat

# Adjuntar ISO
VBoxManage storageattach "bcs-validation" --storagectl "NVMe" --port 0 --device 0 --type dvddrive \
  --medium "/ruta/a/ubuntu-24.04-live-server-amd64.iso"
```

---

## 3. Instalar Ubuntu 24.04

### 3.1. Arranque

1. Iniciar la VM
2. Seleccionar **Try or Install Ubuntu Server**
3. Esperar a que cargue el instalador

### 3.2. Configuración del instalador

Paso a paso:

| Paso | Acción |
|---|---|
| Idioma | English |
| Teclado | Layout: Spanish, Variant: Spanish (o el que corresponda) |
| Network | DHCP automático (NAT) — confirmar que aparece IP |
| Proxy | Dejar vacío |
| Mirror | Dejar por defecto |
| Storage | **Usar todo el disco NVMe** con particionado por defecto |
| Profile | `tech` / `tech` / `BCS Validation VM` / `tech@local` |
| SSH Server | **Marcar Install OpenSSH server** |
| Featured snaps | Ninguno |
| Instalar | Confirmar y esperar (~5-10 min) |

**IMPORTANTE:** El instalador crea automáticamente una partición EFI (ESP) en `/boot/efi`. Esto es necesario para que `bcs doctor` detecte firmware UEFI.

### 3.3. Post-instalación

1. La VM se reinicia automáticamente
2. Extraer la ISO del lector virtual (si no se expulsa sola)
3. La VM debe arrancar desde el disco NVMe
4. Hacer login con `tech` / contraseña elegida

---

## 4. Verificar instalación

Ejecutar estos comandos uno a uno y confirmar que funcionan:

```bash
# Red
ip a
ping -c 1 8.8.8.8
ping -c 1 google.com

# Sistema
uname -a
lsb_release -a
cat /sys/firmware/efi   # debe existir (es un directorio)

# Disco
lsblk
lsblk -J -b            # JSON output (lo usa el Storage Adapter)
efibootmgr -v          # debe funcionar (lo usa el EFI Adapter)

# Herramientas
python3 --version      # debe ser 3.12.x
git --version
```

---

## 5. Snapshot inicial

Una vez verificada la instalación, crear un snapshot antes de tocar nada:

```bash
# Desde el host (no desde la VM):
VBoxManage snapshot "bcs-validation" take "01-fresh-ubuntu-2404"
```

Este snapshot es el **punto de retorno** para repetir la validación desde cero.

---

## 6. Referencia: accesos

| Dato | Valor |
|---|---|
| Usuario | `tech` |
| Contraseña | (la elegida en instalación) |
| Hostname | `bcs-validation` |
| Red | DHCP NAT (10.0.2.15 típico) |
| SSH | `ssh tech@10.0.2.15` (si se configura bridge) |

---

## 7. Siguiente paso

Ir a [VM_INSTALLATION.md](VM_INSTALLATION.md) para instalar `bcs`.
