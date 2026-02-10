# Armbian en eMMC para BananaPi BPI-R4

Este repositorio nace de la necesidad de tener una imagen basada en **Debian/Ubuntu** corriendo de forma estable en el [BananaPi BPI-R4](https://wiki.banana-pi.org/Banana_Pi_BPI-R4), un router board con SoC MediaTek MT7988A (Filogic 880), 4GB de RAM y almacenamiento eMMC.

## Por que este repo

El BPI-R4 viene de fabrica con OpenWrt en NAND, pero para nuestro caso necesitabamos un sistema basado en Debian con acceso a `apt`, herramientas estandar de Linux, y flexibilidad para desarrollo. Optamos por **Armbian** como distribucion.

### El problema del bootloader: por que frank-w U-Boot

Para que el BPI-R4 arranque desde la eMMC se necesita un **bootloader (U-Boot)** grabado en las particiones de boot de la eMMC. Armbian no incluye bootloader propio para esta placa. Aqui es donde entra **[frank-w/u-boot](https://github.com/frank-w/u-boot)**: es un port mantenido por la comunidad del U-Boot oficial, adaptado especificamente para el BPI-R4 y otros boards MediaTek. Es practicamente **la unica opcion funcional** para arrancar desde eMMC con un sistema que no sea OpenWrt.

El U-Boot de frank-w aporta dos archivos esenciales que se graban en la eMMC:
- **BL2** (`bpi-r4_emmc_bl2.img`) - Se graba en la particion `boot0`. Es lo primero que ejecuta el SoC al encender.
- **FIP** (`bpi-r4_emmc_fip.bin`) - Se graba en la particion 4 (offset sector 13312). Contiene el U-Boot propiamente dicho.

**Sin estos archivos la placa simplemente no arranca** - muestra `System halt!` porque no encuentra bootloader en la eMMC.

### El problema de integracion Armbian + frank-w

Aunque ambos proyectos soportan el BPI-R4, **no estan integrados entre si**. La cadena de boot de frank-w U-Boot espera encontrar un FIT image (`bpi-r4.itb`) que empaqueta kernel, initrd y DTB en un solo archivo, pero Armbian no genera ese archivo. Ademas, el mecanismo de DTB overlays de frank-w es incompatible con los `.dtbo` de Armbian en las versiones actuales: al intentar aplicar overlays, el device tree se corrompe y el kernel no detecta la eMMC.

Esto significa que **no hay un camino directo** para instalar Armbian y que arranque automaticamente. Hay que configurar manualmente el boot despues de la instalacion, que es exactamente lo que documentamos aqui.

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

Lo esencial para que funcione son **3 cosas**:

1. **Bootloader frank-w grabado en la eMMC** - BL2 en `boot0`, FIP en particion 4. Sin esto no arranca nada.
2. **Imagen de Armbian en la eMMC** - Se escribe con `dd` sobre `/dev/mmcblk0`. Contiene el rootfs, kernel, initrd y DTBs.
3. **`/uEnv.txt` con override del comando de boot** - Esta es la pieza clave que une todo.

El U-Boot de frank-w lee `/uEnv.txt` al arrancar y permite sobreescribir cualquier variable, incluyendo comandos internos. Sobreescribimos `newboot` (el comando que normalmente intenta cargar el FIT image inexistente) para que en su lugar cargue kernel, initrd y DTB por separado usando `booti`:

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

---

## Glosario para principiantes

Si eres nuevo en estos temas, aqui van los terminos que usamos en este proyecto explicados de forma simple:

**SoC (System on Chip)** - Un chip que tiene "todo adentro": procesador, memoria, controladores de red, etc. Es como si tu PC completa estuviera en un solo chip. El BPI-R4 usa el MediaTek MT7988A.

**eMMC** - La memoria interna de la placa, como el disco duro de una PC pero soldado en la placa. Es donde instalamos Armbian. Ejemplo: cuando haces `dd if=imagen.img of=/dev/mmcblk0` estas escribiendo directamente sobre esa memoria, como si formatearas un disco duro y le pusieras un sistema operativo.

**NAND** - Otro tipo de memoria interna donde viene OpenWrt de fabrica. La placa tiene dos: NAND (con OpenWrt) y eMMC (donde ponemos Armbian). Un **DIP switch** fisico elige desde cual arranca.

**Bootloader / U-Boot** - El primer programa que se ejecuta al encender la placa. Su unico trabajo es cargar el sistema operativo. Es como el BIOS de una PC: tu no lo ves, pero sin el no arranca nada. Ejemplo: cuando enciendes tu PC y ves el logo del fabricante antes de Windows/Linux, eso es el bootloader trabajando.

**BL2 y FIP** - Son las dos partes del bootloader. BL2 es la primera etapa (muy pequena, solo sabe inicializar la RAM y buscar el FIP), y el FIP es la segunda etapa que contiene el U-Boot completo. Es como un cohete de dos fases: la primera enciende los motores, la segunda pone en orbita.

**Kernel** - El nucleo del sistema operativo. Es el programa que habla directamente con el hardware (discos, red, pantalla) y permite que todo lo demas funcione. Ejemplo: cuando conectas un USB, es el kernel quien lo detecta. En nuestro caso es el archivo `/boot/Image`.

**DTB (Device Tree Blob)** - Un archivo que le dice al kernel que hardware tiene la placa: "tienes 4GB de RAM, tienes eMMC en tal direccion, tienes 4 puertos de red...". Sin este archivo el kernel no sabe que hardware manejar. Ejemplo: es como darle un mapa de la ciudad a un repartidor; sin el mapa, no sabe a donde ir. Archivo: `/boot/dtb/mediatek/mt7988a-bananapi-bpi-r4-emmc.dtb`.

**DTB Overlay (.dtbo)** - Un parche pequeno que modifica el DTB base. En vez de crear un DTB completo para cada variante de la placa (SD, eMMC, WiFi), se aplican parches sobre el base. Problema: el mecanismo de frank-w U-Boot para aplicar estos parches no funciona bien con los de Armbian.

**initrd / uInitrd** - Un mini-sistema de archivos que el kernel carga en RAM antes de montar el disco real. Contiene drivers y scripts minimos para poder acceder al disco donde esta el sistema completo. Ejemplo: es como un kit de emergencia que traes en el carro; lo usas solo para arrancar, despues ya no lo necesitas.

**FIT image (.itb)** - Un archivo que empaqueta kernel + DTB + initrd en un solo "paquete". Es comodo porque cargas un solo archivo en vez de tres. Problema: Armbian no genera este archivo y cuando lo creamos manualmente, el mecanismo de overlays falla.

**booti vs bootm** - Dos comandos de U-Boot para arrancar Linux. `bootm` arranca desde un FIT image (todo empaquetado), `booti` arranca cargando kernel, initrd y DTB por separado. En nuestro caso `booti` funciona y `bootm` no, por el problema de overlays.

**uEnv.txt** - Un archivo de texto que U-Boot lee al arrancar. Cualquier variable definida ahi sobreescribe las de U-Boot. Es como un archivo de configuracion que tiene la ultima palabra. Ejemplo: si U-Boot dice "arranca con bootm" pero uEnv.txt dice "arranca con booti", gana uEnv.txt.

**dd** - Comando de Linux para copiar datos byte a byte. Se usa para "grabar" imagenes en discos. Ejemplo: `dd if=armbian.img of=/dev/mmcblk0` copia la imagen de Armbian directamente a la eMMC, como cuando grabas una imagen ISO en un USB para instalar un sistema operativo.

**Puerto serial / UART** - Una conexion directa de "texto" entre la placa y una PC. Envia y recibe caracteres como un chat primitivo. Es la forma mas basica de comunicarse con el hardware cuando no hay pantalla ni red. Se conecta con un adaptador **FTDI USB-to-TTL** (un cablecito USB que convierte senales seriales).

**SCP** - Copia de archivos por red usando SSH. Ejemplo: `scp archivo.img root@192.168.1.1:/tmp/` copia un archivo desde tu PC al dispositivo remoto, como un "copiar y pegar" pero entre dos maquinas por la red.

**DHCP** - Protocolo que asigna IPs automaticamente. Cuando conectas la placa a la red, el router le asigna una IP (como 192.168.13.228) sin que tengas que configurar nada. Problema: el BPI-R4 genera una MAC address random en cada boot, asi que la IP puede cambiar.

**netplan** - La herramienta que usa Armbian/Ubuntu para configurar la red. Se configura con archivos YAML en `/etc/netplan/`. Ejemplo: para decirle "usa DHCP en el puerto WAN", escribes un archivo con `dhcp4: true` bajo la interfaz `wan`.
