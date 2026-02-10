# SKILLS.md - Capacidades y Habilidades del Agente

Este archivo documenta las habilidades que el agente de IA ha desarrollado y probado en este proyecto. Sirve como referencia para futuras sesiones: si necesitas que el agente haga algo listado aqui, ya se ha probado y funciona.

---

## Habilidades de Hardware/Embedded

### Interaccion con puerto serial
- **Que puede hacer:** Conectarse a `/dev/ttyUSB0` via pyserial, enviar comandos, leer respuestas fragmentadas, y tomar decisiones basadas en el output
- **Herramienta:** Python con `serial.Serial()` ejecutado desde Bash
- **Limitacion:** Necesita que el usuario libere el puerto primero (`killall screen`, etc.)
- **Patron probado:**
  ```python
  ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
  def send_cmd(cmd, wait=3):
      ser.write((cmd + '\n').encode())
      ser.flush()
      time.sleep(wait)
      return ser.read(ser.in_waiting).decode('utf-8', errors='replace')
  ```
- **Nota importante:** Los datos seriales llegan fragmentados. El agente debe esperar suficiente tiempo y puede necesitar multiples lecturas para obtener una respuesta completa. Los scripts rigidos (expect, pyserial con patrones fijos) fallan frecuentemente por esto. La IA se adapta mejor porque interpreta fragmentos parciales.

### Flasheo de eMMC via OpenWrt
- **Que puede hacer:** Transferir archivos via SCP, ejecutar dd para flashear bootloader y sistema operativo en eMMC
- **Ruta probada:** PC -> SCP -> OpenWrt (/tmp) -> dd -> eMMC
- **Gotchas conocidos:**
  - BusyBox dd no soporta `status=progress`
  - Las particiones pueden no aparecer automaticamente despues de dd
  - El offset de la particion 4 (FIP) es sector 13312

### Control de U-Boot via serial
- **Que puede hacer:** Escapar del Boot Menu (ESC), ejecutar comandos en prompt `BPI-R4>`, configurar variables, cargar archivos desde eMMC, bootear kernel
- **Comandos clave dominados:**
  - `printenv <var>` - ver variables
  - `setenv <var> <value>` - setear variables
  - `load mmc 0:5 <addr> <file>` - cargar archivo de eMMC a RAM
  - `booti <kernel> <initrd> <dtb>` - arrancar Linux
  - `bootm <addr>#<config>` - arrancar desde FIT image
- **Conocimiento de la cadena de boot frank-w:**
  ```
  bootcmd -> loadenv (uEnv.txt) -> bootmenu -> newboot
  newboot -> checkrd -> setbootconf -> buildargs -> loadkernel -> bootm
  ```

### Creacion de FIT images
- **Que puede hacer:** Crear archivos .its y generar .itb con mkimage
- **Estado:** Funcional pero NO recomendado para Armbian 26.2.0 (ver AGENT.md)
- **Conocimiento adquirido:**
  - `load` address no debe coincidir con `loadaddr` de U-Boot
  - Los DTB overlays (.dtbo) de Armbian no son compatibles con el mecanismo FIT overlay de frank-w U-Boot
  - `booti` directo es la solucion correcta

---

## Habilidades de Sistema/Red

### Configuracion de red en Armbian
- **Que puede hacer:** Configurar interfaces de red via netplan, dhcpcd, verificar conectividad
- **Interfaces del BPI-R4:**
  - `eth0` - interfaz base (DSA master)
  - `wan@eth0` - puerto WAN
  - `lan1@eth0` a `lan3@eth0` - puertos LAN
  - `eth1`, `eth2` - SFP
- **Fix conocido:** netplan necesita `wan*` en vez de `wan[0-9]*`

### Gestion de paquetes en Armbian
- **Que puede hacer:** `apt update`, `apt upgrade`, instalar paquetes
- **Metodo:** Via serial o SSH
- **Tip:** Usar `DEBIAN_FRONTEND=noninteractive` para upgrades no interactivos

### SSH remoto
- **Que puede hacer:** Conectar por SSH, ejecutar comandos, transferir archivos con SCP
- **Gotcha:** Las claves SSH cambian al reinstalar, usar `ssh-keygen -R` para limpiar
- **Autenticacion:** sshpass para password, o clave publica

---

## Habilidades de Diagnostico

### Debug de boot
- **Que puede hacer:** Analizar secuencia de boot, identificar errores de U-Boot, diagnosticar kernel panics
- **Errores que sabe resolver:**
  - `VFS: Unable to mount root fs` -> problema de DTB o bootargs
  - `new format image overwritten` -> colision de direcciones de memoria
  - `Volume ubootenv not found` -> normal en boot eMMC, usar uEnv.txt
  - `System halt!` -> eMMC vacia, flashear primero
  - Boot loop -> ESC en Boot Menu, boot manual

### Verificacion de versiones
- **Que puede hacer:** Consultar GitHub API para releases de frank-w/u-boot, buscar imagenes de Armbian actualizadas
- **Herramientas:** `gh api`, `wget`, web search

---

## Habilidades de Documentacion

### Actualizacion de documentacion tecnica
- **Que puede hacer:** Actualizar INSTALACION_ARMBIAN_EMMC.md, crear AGENT.md, SKILLS.md
- **Estilo:** Documentacion pragmatica orientada a resolver problemas, con versiones especificas y gotchas conocidos

---

## Flujo de trabajo recomendado con el agente

### Para instalar Armbian en un BPI-R4 nuevo:
1. Decirle al agente que revise el proyecto (`revisa nuestro proyecto`)
2. Pedirle que descargue las versiones mas recientes
3. Conectar el BPI-R4 a la red con OpenWrt desde NAND
4. Decirle la IP del dispositivo
5. **Dejar que el agente trabaje autonomamente** - transferira archivos, flasheara eMMC, se conectara al serial, configurara boot y red
6. Solo intervenir para: cambiar DIP switches, resetear fisicamente, liberar puerto serial

### Para diagnosticar problemas de boot:
1. Liberar el puerto serial (`killall screen`)
2. Decirle al agente que se conecte al serial
3. Dejar que investigue: leera U-Boot env, probara boot, analizara errores

### Para actualizar el sistema:
1. Decirle la IP actual del BPI-R4
2. Pedirle que haga `apt update && apt upgrade`
3. Si cambia el kernel, pedirle que verifique que el autoboot sigue funcionando

---

## Limitaciones conocidas

- **No puede operar DIP switches** - Requiere intervencion fisica del usuario
- **No puede resetear el dispositivo** - Necesita que el usuario presione boton o desconecte power
- **Puerto serial exclusivo** - Solo un proceso puede usar `/dev/ttyUSB0` a la vez
- **Timeouts en comandos largos** - `dd` de 1.2GB tarda minutos, el agente debe usar timeouts largos
- **MAC address random** - U-Boot genera MAC random al arrancar, la IP DHCP puede cambiar entre boots
