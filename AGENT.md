# AGENT.md - Registro de Trabajo con IA

Este archivo documenta el trabajo realizado con un agente de IA (Claude) en el proyecto BananaPi BPI-R4. El objetivo es dejar registro de las decisiones, problemas resueltos y metodologias usadas para que futuras sesiones (o personas) puedan entender el contexto.

---

## Sesion 2026-02-10: Instalacion de Armbian en BPI-R4 nuevo

### Objetivo
Instalar Armbian en la eMMC de un BananaPi BPI-R4 nuevo (4GB RAM) y lograr que arranque automaticamente sin intervencion manual.

### Versiones utilizadas
- **Armbian:** 26.2.0-trunk.385 -> actualizado a 26.2.0-trunk.414 (Ubuntu Noble, Kernel 6.12.69)
- **U-Boot frank-w:** 2026.01 (CI-BUILD-2026-01-bpi-2026.01-2026-01-16_2142)
- **BPI-R4:** modelo 4GB RAM

### Flujo de trabajo

1. **Verificacion del repositorio** - Repo sincronizado con GitHub
2. **Descarga de archivos actualizados** - Armbian y bootloaders frank-w mas recientes
3. **Flasheo de eMMC** - Via SCP a OpenWrt + dd
4. **Primer boot manual** - Via puerto serial con booti
5. **Configuracion de red** - netplan con fix del match `wan*`
6. **apt upgrade** - Kernel actualizado de 6.12.63 a 6.12.69
7. **Intentos de autoboot con FIT image** - Multiple iteraciones (ver Problemas)
8. **Solucion final** - Override de `newboot` en uEnv.txt con booti

### Problemas encontrados y resueltos

#### 1. BusyBox dd no soporta status=progress
- **Contexto:** El script `install_armbian_emmc.sh` usaba `dd ... status=progress`
- **Error:** BusyBox muestra el help de dd y falla
- **Solucion:** Ejecutar los comandos dd manualmente sin `status=progress`

#### 2. Particiones eMMC no detectadas en OpenWrt
- **Contexto:** Despues de escribir la imagen, `/dev/mmcblk0p4` no existia
- **Solucion:** Escribir FIP en offset directo: `dd ... of=/dev/mmcblk0 bs=512 seek=13312`

#### 3. SSH host key changed
- **Contexto:** La IP ya tenia una clave SSH de otro dispositivo
- **Solucion:** `ssh-keygen -R <IP>` antes de conectar

#### 4. Netplan no asigna IP a wan
- **Contexto:** La config de Armbian tenia `wan[0-9]*` pero la interfaz es `wan` (sin digito)
- **Solucion:** Cambiar match a `wan*`

#### 5. dhclient no disponible
- **Contexto:** Para la configuracion inicial de red, `dhclient` no existe en Armbian minimal
- **Solucion:** Usar `dhcpcd wan` para la primera conexion, luego configurar netplan

#### 6. Armbian 26.2.0 no incluye bpi-r4.itb
- **Contexto:** frank-w U-Boot espera un FIT image que Armbian no genera
- **Intentos:** Se creo bpi-r4.itb con mkimage usando .its descriptor
- **Resultado:** El FIT se crea pero el boot falla (ver siguientes problemas)

#### 7. FIT image: "new format image overwritten"
- **Contexto:** El FIT se carga en `loadaddr=0x46000000` y el kernel tenia `load=0x46000000`
- **Causa:** bootm intenta extraer el kernel a la misma direccion donde esta el FIT
- **Solucion parcial:** Cambiar kernel load a `0x48000000`

#### 8. FIT image: Kernel panic con DTB overlay
- **Contexto:** U-Boot genera `bootconf=#conf-base#ov-emmc` que aplica overlay sobre DTB base
- **Causa:** El mecanismo de overlay no funciona correctamente con los .dtbo de Armbian
- **Intentos:**
  - Usar DTB completo en vez de overlay -> DTB se corrompe porque bootm intenta aplicar overlay sobre un DTB completo
  - Anular `checkmmc` para evitar overlay -> kernel arranca pero no detecta eMMC
  - Anular `ovmmc` -> se regenera por `setbootconf`
- **Conclusion:** El mecanismo FIT+overlay de frank-w u-boot 2026.01 es incompatible con Armbian 26.2.0

#### 9. SOLUCION FINAL: Override de newboot en uEnv.txt
- **Descubrimiento clave:** `loadenvfile` usa `env import -t` que permite sobreescribir CUALQUIER variable de U-Boot desde uEnv.txt, incluyendo comandos como `newboot`
- **Solucion:** Definir `newboot` en `/uEnv.txt` para usar `booti` con carga individual de kernel, initrd y DTB
- **Resultado:** Boot automatico funcional tras cada reinicio

### Metodologia: IA como interfaz serial

El agente de IA (Claude) se conecto directamente al puerto serial `/dev/ttyUSB0` usando pyserial para:
- Enviar comandos a U-Boot y Armbian
- Leer y analizar las respuestas (fragmentadas)
- Diagnosticar errores en tiempo real
- Probar multiples soluciones iterativamente

Esto fue significativamente mas efectivo que scripts rigidos porque:
- Los scripts serial envian comandos que a veces llegan cortados
- La IA puede interpretar respuestas parciales
- La IA puede cambiar de estrategia cuando algo falla
- No requiere que el usuario este presente para cada decision

### Patron de codigo para interaccion serial con IA

```python
import serial, time

ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
ser.reset_input_buffer()

def send_cmd(cmd, wait=3):
    """Envia comando y espera respuesta"""
    ser.write((cmd + '\n').encode())
    ser.flush()
    time.sleep(wait)
    return ser.read(ser.in_waiting).decode('utf-8', errors='replace')

# La IA ejecuta este patron en cada turno:
# 1. Envia uno o mas comandos
# 2. Lee la respuesta (puede ser fragmentada)
# 3. Analiza el resultado
# 4. Decide el siguiente paso
```

### Archivos modificados/creados en esta sesion
- `/uEnv.txt` - Override de newboot para autoboot
- `/etc/netplan/10-dhcp-all-interfaces.yaml` - Fix de match wan*
- `/boot/extlinux/extlinux.conf` - DTB corregido a emmc
- `/boot/bpi-r4.its` - Descriptor FIT (para referencia)
- `/boot/bpi-r4.itb` + `/bpi-r4.itb` - FIT image (no se usa, queda como referencia)

### Lecciones aprendidas

1. **No confiar en FIT overlays entre frank-w U-Boot y Armbian** - Son incompatibles en las versiones actuales
2. **uEnv.txt es extremadamente poderoso** - Puede sobreescribir cualquier variable/comando de U-Boot
3. **booti > bootm para Armbian** - Cargar componentes individualmente es mas confiable que FIT
4. **Los symlinks de /boot se actualizan con apt upgrade** - La solucion en uEnv.txt sobrevive actualizaciones de kernel
5. **La comunicacion serial es fragil** - Una IA manejando la interaccion es mejor que scripts rigidos

---

## Notas para futuras sesiones

- La IP del BPI-R4 cambia con cada boot (DHCP). Verificar con `arp-scan` o via serial.
- Si se necesita acceso SSH sin password, copiar clave publica SSH.
- El password de root fue cambiado del default `1234` a uno personalizado.
- Si hay actualizaciones de Armbian que cambien la estructura de /boot, puede ser necesario ajustar los paths en uEnv.txt.
