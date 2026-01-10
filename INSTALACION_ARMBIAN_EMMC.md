# Instalacion de Armbian en eMMC del BananaPi BPI-R4

## Requisitos Previos
- BPI-R4 arrancando desde NAND con OpenWrt funcional
- Conexion de red al BPI-R4 (IP: 192.168.1.1)
- Cable serial USB conectado al PC (aparece como /dev/ttyUSB0)
- Archivos necesarios en el PC host

## Paso 1: Descargar Archivos Necesarios

```bash
cd /home/omar/BananaPi-BPI-R4

# Descargar BL2 y FIP especificos para eMMC de frank-w
wget "https://github.com/frank-w/u-boot/releases/latest/download/bpi-r4_emmc_bl2.img"
wget "https://github.com/frank-w/u-boot/releases/latest/download/bpi-r4_emmc_fip.bin"

# Descargar imagen de Armbian desde armbian.com
# Descomprimir si es necesario:
xz -dk armbian-bpi-r4.img.xz
```

## Paso 2: Transferir Archivos al BPI-R4 (via SCP)

```bash
# Transferir bootloaders
scp -O bpi-r4_emmc_bl2.img bpi-r4_emmc_fip.bin root@192.168.1.1:/tmp/

# Transferir imagen de Armbian (~1.2GB)
scp -O armbian-bpi-r4.img root@192.168.1.1:/tmp/
```

## Paso 3: Escribir en eMMC (desde OpenWrt)

Conectarse al BPI-R4 por SSH y ejecutar:

```bash
# Desbloquear particion boot0
echo 0 > /sys/block/mmcblk0boot0/force_ro

# Escribir BL2 en boot0
dd if=/tmp/bpi-r4_emmc_bl2.img of=/dev/mmcblk0boot0

# Escribir imagen de Armbian en eMMC
dd if=/tmp/armbian-bpi-r4.img of=/dev/mmcblk0 bs=1M status=progress

# Escribir FIP en particion 4
dd if=/tmp/bpi-r4_emmc_fip.bin of=/dev/mmcblk0p4

# Habilitar boot desde eMMC
mmc bootpart enable 1 1 /dev/mmcblk0

sync
```

## Paso 4: Cambiar DIP Switch para eMMC

Apagar el BPI-R4 y configurar:

```
SW3-A = 1 (ON)
SW3-B = 0 (OFF)
```

## Paso 5: Primer Boot Manual desde U-Boot

El U-Boot de frank-w tiene `root=/dev/mmcblk0p6` por defecto, pero Armbian usa `mmcblk0p5`. Es necesario arrancar manualmente la primera vez.

### Opcion A: Comandos Manuales

Conectar al puerto serial (115200 baud) y cuando aparezca el prompt `BPI-R4>`, ejecutar:

```
setenv root /dev/mmcblk0p5 rootfstype=ext4 rootwait
run newboot
```

### Opcion B: Script Automatizado

Ejecutar el script ANTES de encender el BPI-R4:

```bash
sudo python3 uboot_autoboot.py -p /dev/ttyUSB0
```

Luego encender o resetear el BPI-R4. El script detectara U-Boot y enviara los comandos automaticamente.

## Paso 6: Configurar Boot Automatico (desde Armbian)

Una vez dentro de Armbian (usuario: root, password: 1234), ejecutar:

### 6.1 Crear archivo uEnv.txt para corregir particion root

```bash
echo "root=/dev/mmcblk0p5 rootfstype=ext4 rootwait" | sudo tee /uEnv.txt
```

### 6.2 Corregir DTB en extlinux.conf (cambiar SD a eMMC)

```bash
sudo sed -i 's/mt7988a-bananapi-bpi-r4-sd.dtb/mt7988a-bananapi-bpi-r4-emmc.dtb/' /boot/extlinux/extlinux.conf
```

### 6.3 Verificar que bpi-r4.itb existe

```bash
ls -lh /boot/bpi-r4.itb /bpi-r4.itb
```

Ambos archivos deben existir (~27MB). Si `/bpi-r4.itb` no existe:

```bash
sudo cp /boot/bpi-r4.itb /
```

### 6.4 Reiniciar y verificar boot automatico

```bash
sudo reboot
```

El sistema deberia arrancar automaticamente sin intervencion.

---

## Credenciales de Armbian
- **Usuario:** root
- **Password:** 1234 (te pedira cambiarla en el primer login)

---

## Solucion de Problemas

### Error: "VFS: Cannot open root device mmcblk0p6"
La variable `root` de U-Boot apunta a la particion incorrecta. Solucion:

1. En el prompt `BPI-R4>`:
   ```
   setenv root /dev/mmcblk0p5 rootfstype=ext4 rootwait
   run newboot
   ```

2. Una vez en Armbian, crear `/uEnv.txt`:
   ```bash
   echo "root=/dev/mmcblk0p5 rootfstype=ext4 rootwait" | sudo tee /uEnv.txt
   ```

### Error: "Bad Linux ARM64 Image magic!"
Se intento cargar `vmlinuz` en lugar de `Image`. El comando `booti` necesita el kernel descomprimido. Usar `boot/Image` en lugar de `boot/vmlinuz-*`.

### Error: "Volume ubootenv not found" al hacer saveenv
Normal cuando se arranca desde eMMC. El entorno de U-Boot esta configurado para guardarse en UBI (NAND). Usar `/uEnv.txt` en su lugar.

### Boot manual funciona pero automatico no
1. Verificar que existe `/uEnv.txt` con `root=/dev/mmcblk0p5`
2. Verificar que existe `/bpi-r4.itb`
3. En U-Boot, ejecutar `printenv root` para ver el valor actual

### Comandos de boot manual completos (si newboot falla)

```
setenv bootargs console=ttyS0,115200 root=/dev/mmcblk0p5 rootwait rw
load mmc 0:5 0x46000000 boot/Image
load mmc 0:5 0x48000000 boot/uInitrd
load mmc 0:5 0x47000000 boot/dtb/mediatek/mt7988a-bananapi-bpi-r4-emmc.dtb
booti 0x46000000 0x48000000 0x47000000
```

---

## Informacion Tecnica

### Estructura de Particiones en eMMC
| Particion | Dispositivo | Contenido |
|-----------|-------------|-----------|
| boot0 | /dev/mmcblk0boot0 | BL2 (bootloader stage 2) |
| p1-p3 | /dev/mmcblk0p1-3 | Reservadas |
| p4 | /dev/mmcblk0p4 | FIP (Firmware Image Package) |
| p5 | /dev/mmcblk0p5 | Root filesystem (ext4) - Armbian |

### Direcciones de Memoria para Boot Manual
| Componente | Direccion |
|------------|-----------|
| Kernel (Image) | 0x46000000 |
| DTB | 0x47000000 |
| Initrd | 0x48000000 |

### Archivos Clave
| Archivo | Ubicacion | Descripcion |
|---------|-----------|-------------|
| bpi-r4.itb | / y /boot/ | FIT image (kernel+dtb+initrd empaquetados) |
| uEnv.txt | / | Variables de entorno para U-Boot |
| Image | /boot/ | Kernel descomprimido (symlink) |
| uInitrd | /boot/ | Initrd (symlink) |
| extlinux.conf | /boot/extlinux/ | Configuracion de boot alternativa |

### Variables U-Boot Importantes
| Variable | Valor Correcto | Descripcion |
|----------|---------------|-------------|
| root | /dev/mmcblk0p5 rootfstype=ext4 rootwait | Particion root |
| fit | bpi-r4.itb | Archivo FIT image |
| partition | 0:5 | Particion de boot (mmc 0, part 5) |
| device | mmc | Dispositivo de boot |

---

## Scripts Incluidos

### uboot_autoboot.py
Script Python para automatizar el boot manual. Detecta U-Boot y envia comandos.

```bash
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
- https://www.fw-web.de/dokuwiki/doku.php?id=en:bpi-r4:start
- https://forum.banana-pi.org/t/bpi-r4-debian-or-ubuntu-on-emmc/19357

---

*Documentacion actualizada: 2026-01-09*
*Probado exitosamente con Armbian y U-Boot de frank-w*
