# Instalacion de Armbian en eMMC del BananaPi BPI-R4

## Versiones Probadas

| Componente | Version | Fecha |
|------------|---------|-------|
| Armbian | 26.2.0-trunk.414 (community) Ubuntu Noble | 2026-02-03 |
| Kernel | 6.12.69-current-filogic | 2026-02-09 |
| U-Boot (frank-w) | 2026.01 (CI-BUILD-2026-01-bpi-2026.01-2026-01-16_2142) | 2026-01-16 |
| BPI-R4 | 4GB RAM | - |

## Requisitos Previos
- BPI-R4 arrancando desde NAND con OpenWrt funcional
- Conexion de red al BPI-R4 (la IP depende de tu red, ej: 192.168.13.236)
- Cable serial USB conectado al PC (aparece como /dev/ttyUSB0)
- Archivos necesarios en el PC host

## Paso 1: Descargar Archivos Necesarios

```bash
cd /home/omar/BananaPi-BPI-R4

# Descargar BL2 y FIP especificos para eMMC de frank-w (4GB RAM)
wget -O bpi-r4_emmc_bl2.img "https://github.com/frank-w/u-boot/releases/latest/download/bpi-r4_emmc_bl2.img"
wget -O bpi-r4_emmc_fip.bin "https://github.com/frank-w/u-boot/releases/latest/download/bpi-r4_emmc_fip.bin"

# Para modelo 8GB RAM, usar las variantes _8GB:
# wget -O bpi-r4_emmc_bl2.img "https://github.com/frank-w/u-boot/releases/latest/download/bpi-r4_emmc_8GB_bl2.img"
# wget -O bpi-r4_emmc_fip.bin "https://github.com/frank-w/u-boot/releases/latest/download/bpi-r4_emmc_8GB_fip.bin"

# Descargar imagen de Armbian (community, Ubuntu Noble)
# Obtener URL actualizada en: https://www.armbian.com/bananapi-r4/
# o en: https://github.com/armbian/community/releases
wget -O armbian-bpi-r4.img.xz "https://github.com/armbian/community/releases/download/26.2.0-trunk.385/Armbian_community_26.2.0-trunk.385_Bananapir4_noble_current_6.12.63_minimal.img.xz"

# Descomprimir
xz -dk armbian-bpi-r4.img.xz
```

## Paso 2: Transferir Archivos al BPI-R4 (via SCP)

```bash
# Transferir bootloaders, imagen y script de instalacion
scp -O bpi-r4_emmc_bl2.img bpi-r4_emmc_fip.bin armbian-bpi-r4.img install_armbian_emmc.sh root@<IP_DEL_BPI-R4>:/tmp/
```

**Nota:** La IP depende de como este conectado el BPI-R4 a tu red. Si OpenWrt viene con IP fija 192.168.1.1, usala. Si esta conectado a un DHCP, busca la IP asignada.

## Paso 3: Escribir en eMMC (desde OpenWrt)

### Opcion A: Comandos manuales por SSH

```bash
ssh root@<IP_DEL_BPI-R4>

# Desbloquear particion boot0
echo 0 > /sys/block/mmcblk0boot0/force_ro

# Escribir BL2 en boot0
dd if=/tmp/bpi-r4_emmc_bl2.img of=/dev/mmcblk0boot0

# Escribir imagen de Armbian en eMMC (SIN status=progress en BusyBox)
dd if=/tmp/armbian-bpi-r4.img of=/dev/mmcblk0 bs=1M conv=fsync

# Escribir FIP en particion 4
# NOTA: En OpenWrt, /dev/mmcblk0p4 puede no aparecer automaticamente.
# Si no existe, usar el offset directo:
sync && sleep 2
if [ -b /dev/mmcblk0p4 ]; then
    dd if=/tmp/bpi-r4_emmc_fip.bin of=/dev/mmcblk0p4
else
    dd if=/tmp/bpi-r4_emmc_fip.bin of=/dev/mmcblk0 bs=512 seek=13312 conv=notrunc
fi

# Habilitar boot desde eMMC
mmc bootpart enable 1 1 /dev/mmcblk0

sync
```

**IMPORTANTE:** El BusyBox de OpenWrt NO soporta `dd ... status=progress`. Si usas el script `install_armbian_emmc.sh`, este ya maneja ese caso.

### Opcion B: Script automatizado

```bash
ssh root@<IP_DEL_BPI-R4> "sh /tmp/install_armbian_emmc.sh"
```

## Paso 4: Cambiar DIP Switch para eMMC

Apagar el BPI-R4 y configurar:

```
SW3-A = 1 (ON)
SW3-B = 0 (OFF)
```

## Paso 5: Primer Boot Manual desde U-Boot

El U-Boot de frank-w v2026.01 tiene un **boot menu** que intenta arrancar usando FIT image (`bpi-r4.itb`). En una instalacion nueva de Armbian, este archivo no existe, asi que el boot automatico falla.

Es necesario arrancar manualmente la primera vez via puerto serial.

### Opcion A: Comandos Manuales

Conectar al puerto serial (115200 baud). U-Boot mostrara un **Boot Menu**. Presionar **ESC** para salir al prompt `BPI-R4>`, luego ejecutar:

```
setenv bootargs console=ttyS0,115200 root=/dev/mmcblk0p5 rootfstype=ext4 rootwait rw
load mmc 0:5 0x46000000 boot/Image
load mmc 0:5 0x48000000 boot/uInitrd
load mmc 0:5 0x47000000 boot/dtb/mediatek/mt7988a-bananapi-bpi-r4-emmc.dtb
booti 0x46000000 0x48000000 0x47000000
```

**NOTA:** NO usar `run newboot` en esta version. El mecanismo FIT con DTB overlays de frank-w u-boot 2026.01 no es compatible con los `.dtbo` de Armbian 26.2.0 y causa kernel panic.

### Opcion B: Script Automatizado

```bash
sudo python3 uboot_autoboot.py -p /dev/ttyUSB0 --manual
```

Usar `--manual` para enviar los comandos individuales de carga (load+booti) en vez de `run newboot`.

**ADVERTENCIA sobre scripts de puerto serial:** Los scripts que interactuan con el puerto serial (pyserial, expect) pueden enviar o recibir la informacion por trozos fragmentados, lo que causa que los comandos lleguen cortados al dispositivo. Esto es un problema inherente a la comunicacion serial asincrona. Ver seccion "Interaccion Serial con IA" mas abajo para una solucion robusta.

## Paso 6: Configurar Boot Automatico (desde Armbian)

Una vez dentro de Armbian (usuario: root, password: 1234), ejecutar:

### 6.1 Crear /uEnv.txt con override completo de newboot

Este es el paso **mas critico**. El `/uEnv.txt` debe sobreescribir el comando `newboot` de U-Boot para usar `booti` directamente, evitando el mecanismo FIT/bootm que no funciona con Armbian 26.2.0.

```bash
cat > /uEnv.txt << 'EOF'
root=/dev/mmcblk0p5 rootfstype=ext4 rootwait
newboot=setenv bootargs console=ttyS0,115200 root=/dev/mmcblk0p5 rootfstype=ext4 rootwait rw; load mmc 0:5 0x46000000 boot/Image; load mmc 0:5 0x48000000 boot/uInitrd; load mmc 0:5 0x47000000 boot/dtb/mediatek/mt7988a-bananapi-bpi-r4-emmc.dtb; booti 0x46000000 0x48000000 0x47000000
EOF
```

**Por que se sobreescribe `newboot`:**

El U-Boot de frank-w v2026.01 tiene esta cadena de boot:
1. `bootcmd` -> `loadenv` (lee /uEnv.txt) -> `bootmenu`
2. Menu opcion 3: "Boot from SD/EMMC" -> `run newboot`
3. `newboot` -> `setbootconf` -> `buildargs` -> carga FIT -> `bootm`

El problema esta en el paso 3: `setbootconf` genera `bootconf=#conf-base#ov-emmc`, que le dice a `bootm` que aplique el overlay `ov-emmc` sobre el DTB base. Este mecanismo de overlays de FIT image falla con Armbian porque:
- Armbian 26.2.0 no incluye `bpi-r4.itb` (hay que crearlo)
- Al crear el FIT image, si se usa el DTB base + `.dtbo` overlay, el overlay no se aplica correctamente y el kernel no detecta la eMMC
- Esto causa `Kernel panic: VFS: Unable to mount root fs on unknown-block(179,5)`

La solucion: sobreescribir `newboot` en `/uEnv.txt` para cargar kernel, initrd y DTB por separado con `booti`, que funciona perfectamente.

### 6.2 Corregir DTB en extlinux.conf (cambiar SD a eMMC)

```bash
sudo sed -i 's/mt7988a-bananapi-bpi-r4-sd.dtb/mt7988a-bananapi-bpi-r4-emmc.dtb/' /boot/extlinux/extlinux.conf
```

### 6.3 Configurar red con netplan

Armbian 26.2.0 usa netplan. La config por defecto en `/etc/netplan/10-dhcp-all-interfaces.yaml` tiene `wan[0-9]*` que NO matchea la interfaz `wan` (sin numero). Corregir:

```bash
cat > /etc/netplan/10-dhcp-all-interfaces.yaml << 'EOF'
network:
  version: 2
  renderer: networkd
  ethernets:
    all-eth-interfaces:
      match:
        name: "e*"
      dhcp4: yes
      dhcp6: yes
      ipv6-privacy: yes
    all-lan-interfaces:
      match:
        name: "lan*"
      dhcp4: yes
      dhcp6: yes
      ipv6-privacy: yes
    all-wan-interfaces:
      match:
        name: "wan*"
      dhcp4: yes
      dhcp6: yes
      ipv6-privacy: yes
EOF

netplan apply
```

**Nota:** El match original `wan[0-9]*` requiere un digito despues de "wan". La interfaz DSA del BPI-R4 se llama simplemente `wan`, asi que hay que usar `wan*`.

### 6.4 Actualizar sistema

```bash
apt update && DEBIAN_FRONTEND=noninteractive apt upgrade -y
```

**IMPORTANTE:** Si el upgrade actualiza el kernel, los symlinks `/boot/Image` y `/boot/uInitrd` se actualizan automaticamente, asi que el `newboot` de uEnv.txt seguira funcionando sin cambios.

### 6.5 Reiniciar y verificar

```bash
sudo reboot
```

El sistema debe arrancar automaticamente sin intervencion manual.

---

## Credenciales de Armbian
- **Usuario:** root
- **Password:** 1234 (te pedira cambiarla en el primer login)

---

## Solucion de Problemas

### Kernel panic: "VFS: Unable to mount root fs on unknown-block(179,5)"

**Causa:** El mecanismo de boot con FIT image (`bootm` + `bpi-r4.itb`) no aplica correctamente el DTB overlay de eMMC, lo que deja al kernel sin driver de eMMC.

**Solucion:** Usar `booti` con carga individual de kernel/initrd/DTB. Asegurarse de que `/uEnv.txt` contiene la linea `newboot=...` con `booti` (ver Paso 6.1).

### Error: "new format image overwritten - must RESET"

**Causa:** La variable `loadaddr=0x46000000` de U-Boot es la misma direccion donde se carga el FIT image. Si el FIT image tiene `load = <0x46000000>` para el kernel, `bootm` intenta extraer el kernel a la misma direccion donde esta el FIT, sobrescribiendolo.

**Solucion:** No relevante si se usa la solucion `booti` de uEnv.txt. Si se necesita FIT, el kernel debe tener `load = <0x48000000>` (diferente a `loadaddr`).

### Error: "Bad Linux ARM64 Image magic!"
Se intento cargar `vmlinuz` en lugar de `Image`. El comando `booti` necesita el kernel descomprimido. Usar `boot/Image`.

### Error: "Volume ubootenv not found" al hacer saveenv
Normal cuando se arranca desde eMMC. El entorno de U-Boot esta configurado para guardarse en UBI (NAND). No se puede hacer `saveenv`. Usar `/uEnv.txt` para persistir variables.

### U-Boot queda en boot loop
Si el boot falla repetidamente, U-Boot reentra al menu cada vez. Para escapar:
1. Conectar cable serial
2. Esperar que aparezca el Boot Menu
3. Presionar **ESC** para salir al prompt
4. Ejecutar los comandos manuales de boot (ver Paso 5A)

### BusyBox dd no soporta status=progress
El OpenWrt del BPI-R4 usa BusyBox, que no soporta `dd ... status=progress`. Omitir esa opcion al ejecutar `dd` manualmente.

### Particiones eMMC no aparecen en OpenWrt
Despues de escribir la imagen con `dd`, las particiones `/dev/mmcblk0p*` pueden no aparecer automaticamente. Usar el offset directo para escribir el FIP:
```bash
dd if=/tmp/bpi-r4_emmc_fip.bin of=/dev/mmcblk0 bs=512 seek=13312 conv=notrunc
```

### Netplan no asigna IP a la interfaz wan
La config por defecto de Armbian usa `wan[0-9]*` que no matchea `wan`. Corregir a `wan*` (ver Paso 6.3).

---

## Interaccion Serial con IA

Una leccion importante de este proyecto: los scripts tradicionales (Python con pyserial, Expect) que interactuan con el puerto serial tienen un problema inherente: **la comunicacion serial es asincrona y los datos llegan fragmentados**. Esto causa que:

- Los comandos se envien cortados si no se esperan los prompts correctamente
- Las respuestas se lean incompletas si el timing no es perfecto
- Los scripts fallen intermitentemente dependiendo de la velocidad de la conexion

**Solucion probada:** Usar una IA (como Claude) conectada al puerto serial via `pyserial` funciona mucho mejor que scripts rigidos porque:

1. **La IA interpreta fragmentos**: Puede recibir datos parciales y entender el contexto
2. **Adapta el timing**: Ajusta las esperas segun lo que va recibiendo
3. **Maneja errores en tiempo real**: Si un comando falla, puede decidir que hacer
4. **Debug interactivo**: Puede investigar problemas y probar soluciones sin reiniciar

Ejemplo de conexion serial con IA:
```python
import serial, time

ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)

def send_cmd(cmd, wait=3):
    ser.write((cmd + '\n').encode())
    ser.flush()
    time.sleep(wait)
    return ser.read(ser.in_waiting).decode('utf-8', errors='replace')
```

La IA envia comandos, lee respuestas fragmentadas, y decide los siguientes pasos. Esto fue clave para diagnosticar y resolver el problema del FIT image con DTB overlays.

---

## Informacion Tecnica

### Estructura de Particiones en eMMC
| Particion | Dispositivo | Contenido |
|-----------|-------------|-----------|
| boot0 | /dev/mmcblk0boot0 | BL2 (bootloader stage 2) |
| p1-p3 | /dev/mmcblk0p1-3 | Reservadas |
| p4 | /dev/mmcblk0p4 | FIP (Firmware Image Package) |
| p5 | /dev/mmcblk0p5 | Root filesystem (ext4) - Armbian |

### Direcciones de Memoria para Boot
| Componente | Direccion | Nota |
|------------|-----------|------|
| loadaddr (FIT/kernel) | 0x46000000 | Donde U-Boot carga archivos por defecto |
| DTB | 0x47000000 | Device Tree Blob |
| Initrd (uInitrd) | 0x48000000 | Initial ramdisk |

### Archivos Clave en Armbian
| Archivo | Ubicacion | Descripcion |
|---------|-----------|-------------|
| uEnv.txt | / | Variables y override de comandos U-Boot |
| Image | /boot/ (symlink) | Kernel descomprimido |
| uInitrd | /boot/ (symlink) | Initrd en formato U-Boot |
| extlinux.conf | /boot/extlinux/ | Config de boot alternativa |
| bpi-r4.its | /boot/ | Descriptor FIT image (para referencia) |
| 10-dhcp-all-interfaces.yaml | /etc/netplan/ | Config de red |

### Variables U-Boot Relevantes (frank-w v2026.01)
| Variable | Valor | Descripcion |
|----------|-------|-------------|
| root | /dev/mmcblk0p5 rootfstype=ext4 rootwait | Particion root (leido de uEnv.txt) |
| newboot | (override en uEnv.txt) | Comando de boot sobreescrito |
| loadaddr | 0x46000000 | Direccion de carga por defecto |
| kaddr | 0x46000000 | Direccion del kernel |
| partition | 0:5 | Particion de boot (mmc 0, part 5) |
| device | mmc | Dispositivo de boot |
| bootcmd | setenv bootdelay 3; run loadenv;bootmenu; | Secuencia de arranque |
| bootconf | #conf-base#ov-emmc | Config FIT (generado por setbootconf) |

### Cadena de Boot de frank-w U-Boot v2026.01
```
Power On -> BL2 -> BL31 -> U-Boot
  -> bootcmd: loadenv (lee /uEnv.txt de mmc 0:5) -> bootmenu
    -> Menu opcion 3: "Boot from SD/EMMC" -> run newboot
      -> newboot (SOBREESCRITO por uEnv.txt):
         setenv bootargs ... -> load Image -> load uInitrd -> load DTB -> booti
```

---

## Scripts Incluidos

### uboot_autoboot.py
Script Python para automatizar el primer boot via serial. Detecta U-Boot y envia comandos.

```bash
# Metodo manual (recomendado para Armbian 26.2.0)
sudo python3 uboot_autoboot.py -p /dev/ttyUSB0 --manual

# Metodo simple (solo funciona si bpi-r4.itb existe y es compatible)
sudo python3 uboot_autoboot.py -p /dev/ttyUSB0
```

### uboot_autoboot.exp
Script Expect alternativo con la misma funcionalidad.

```bash
sudo ./uboot_autoboot.exp /dev/ttyUSB0
```

### install_armbian_emmc.sh
Script para ejecutar en OpenWrt que automatiza el Paso 3 (escritura en eMMC).

---

## Referencias
- https://github.com/frank-w/u-boot/releases
- https://www.armbian.com/bananapi-r4/
- https://github.com/armbian/community/releases
- https://www.fw-web.de/dokuwiki/doku.php?id=en:bpi-r4:start
- https://forum.banana-pi.org/t/bpi-r4-debian-or-ubuntu-on-emmc/19357

---

*Documentacion actualizada: 2026-02-10*
*Probado exitosamente con Armbian 26.2.0 + U-Boot frank-w 2026.01 en BPI-R4 4GB*
