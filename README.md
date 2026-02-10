# Armbian en eMMC para BananaPi BPI-R4

Este repositorio nace de la necesidad de tener una imagen basada en **Debian/Ubuntu** corriendo de forma estable en el [BananaPi BPI-R4](https://wiki.banana-pi.org/Banana_Pi_BPI-R4), un router board con SoC MediaTek MT7988A (Filogic 880), 4GB de RAM y almacenamiento eMMC.

## Por que este repo

El BPI-R4 viene de fabrica con OpenWrt en NAND, pero para nuestro caso necesitabamos un sistema basado en Debian con acceso a `apt`, herramientas estandar de Linux, y flexibilidad para desarrollo. Optamos por **Armbian** como distribucion y por los **bootloaders de [frank-w](https://github.com/frank-w/u-boot)** que son los que tienen mejor soporte comunitario para esta placa.

El problema es que **no hay un camino directo** para instalar Armbian en la eMMC del BPI-R4 y que arranque automaticamente. La imagen oficial de Armbian no incluye el FIT image (`bpi-r4.itb`) que el U-Boot de frank-w espera, y el mecanismo de DTB overlays entre ambos proyectos es incompatible en las versiones actuales. Esto obliga a hacer configuraciones manuales post-instalacion que documentamos aqui.

## Que encontraras en este repositorio

| Archivo | Descripcion |
|---------|-------------|
| **[INSTALACION_ARMBIAN_EMMC.md](INSTALACION_ARMBIAN_EMMC.md)** | Guia paso a paso para instalar Armbian en la eMMC, incluyendo descarga de archivos, flasheo, configuracion de autoboot y red |
| **[AGENT.md](AGENT.md)** | Registro detallado del trabajo realizado con IA (Claude), problemas encontrados y soluciones |
| **[SKILLS.md](SKILLS.md)** | Capacidades probadas del agente de IA en este proyecto (serial, boot, red, diagnostico) |
| **install_armbian_emmc.sh** | Script para flashear la eMMC desde OpenWrt (BL2 + imagen Armbian + FIP) |
| **uboot_autoboot.py** | Script Python para automatizar el boot via puerto serial |
| **uboot_autoboot.exp** | Script Expect alternativo para automatizar el boot |

## La solucion en resumen

Despues de multiples intentos con FIT images y `bootm`, la solucion que funciona es **sobreescribir el comando `newboot` de U-Boot** a traves de `/uEnv.txt` para usar `booti` con carga individual de kernel, initrd y DTB:

```
newboot=setenv bootargs console=ttyS0,115200 root=/dev/mmcblk0p5 rootfstype=ext4 rootwait rw; load mmc 0:5 0x46000000 boot/Image; load mmc 0:5 0x48000000 boot/uInitrd; load mmc 0:5 0x47000000 boot/dtb/mediatek/mt7988a-bananapi-bpi-r4-emmc.dtb; booti 0x46000000 0x48000000 0x47000000
```

Esto sobrevive reinicios y actualizaciones de kernel (los symlinks de `/boot` se actualizan automaticamente con `apt upgrade`).

## Versiones probadas

- **Armbian:** 26.2.0-trunk (Ubuntu Noble, kernel 6.12.69)
- **U-Boot:** frank-w 2026.01
- **Hardware:** BananaPi BPI-R4, 4GB RAM

## Debug con IA via puerto serial

Una de las lecciones mas valiosas de este proyecto fue usar un **agente de IA (Claude) conectado directamente al puerto serial** del BPI-R4 a traves de un adaptador **FTDI USB-to-TTL** (en nuestro caso via `/dev/ttyUSB0` a 115200 baud).

Los scripts tradicionales (expect, pyserial con patrones fijos) fallan frecuentemente porque la comunicacion serial es fragil: los datos llegan fragmentados, los comandos a veces se cortan, y los tiempos de respuesta varian. En cambio, la IA puede:

- Interpretar respuestas parciales o fragmentadas
- Cambiar de estrategia cuando algo falla
- Diagnosticar errores en tiempo real (kernel panics, errores de U-Boot, problemas de DTB)
- Iterar sobre soluciones sin intervencion humana

El patron basico que usamos:

```python
import serial, time

ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)

def send_cmd(cmd, wait=3):
    ser.write((cmd + '\n').encode())
    ser.flush()
    time.sleep(wait)
    return ser.read(ser.in_waiting).decode('utf-8', errors='replace')

# La IA ejecuta comandos, lee la respuesta, analiza, y decide el siguiente paso
```

Este enfoque nos permitio resolver en una sola sesion lo que de otra forma habria tomado dias de prueba y error manual.

## Contribuciones

Este es un proyecto en progreso. Si tienes un BPI-R4 y has encontrado mejores formas de hacer el boot, configurar la red, o integrar Armbian con el U-Boot de frank-w, cualquier aporte es bienvenido. Abre un issue o un pull request.

## Enlaces utiles

- [Armbian para BPI-R4](https://www.armbian.com/bananapi-r4/) - Descarga oficial (apunta a `armbian/community` en GitHub)
- [frank-w/u-boot](https://github.com/frank-w/u-boot) - Bootloaders con soporte BPI-R4
- [Wiki BPI-R4](https://wiki.banana-pi.org/Banana_Pi_BPI-R4) - Documentacion oficial del hardware
