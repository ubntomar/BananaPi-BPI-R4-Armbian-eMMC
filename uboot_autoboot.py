#!/usr/bin/env python3
"""
Script para automatizar el boot de Armbian en BPI-R4 desde eMMC
Detecta el prompt de U-Boot y envia los comandos necesarios.

Uso:
    sudo python3 uboot_autoboot.py -p /dev/ttyUSB0

Ejecutar ANTES de encender/reiniciar el BPI-R4.
"""
import serial
import sys
import time
import argparse

# Metodo rapido: solo corregir root y usar newboot (recomendado)
BOOT_COMMANDS_SIMPLE = [
    'setenv root /dev/mmcblk0p5 rootfstype=ext4 rootwait',
    'run newboot',
]

# Metodo manual completo: cargar kernel, initrd y dtb individualmente
BOOT_COMMANDS_MANUAL = [
    'setenv bootargs console=ttyS0,115200 root=/dev/mmcblk0p5 rootwait rw',
    'load mmc 0:5 0x46000000 boot/Image',
    'load mmc 0:5 0x48000000 boot/uInitrd',
    'load mmc 0:5 0x47000000 boot/dtb/mediatek/mt7988a-bananapi-bpi-r4-emmc.dtb',
    'booti 0x46000000 0x48000000 0x47000000',
]


def log(msg, level="INFO"):
    print(f"[{level}] {msg}", file=sys.stderr)


def read_until(ser, patterns, timeout=30):
    """Lee del serial hasta encontrar uno de los patrones o timeout"""
    buffer = ""
    start = time.time()
    while time.time() - start < timeout:
        if ser.in_waiting:
            try:
                chunk = ser.read(ser.in_waiting).decode('utf-8', errors='replace')
                buffer += chunk
                print(chunk, end='', flush=True)

                for pattern in patterns:
                    if pattern in buffer:
                        return pattern, buffer
            except Exception as e:
                log(f"Error leyendo: {e}", "ERROR")
        time.sleep(0.05)
    return None, buffer


def send_command(ser, cmd, wait_prompt=True, timeout=10):
    """Envia un comando y opcionalmente espera el prompt"""
    # Limpiar cualquier dato pendiente antes de enviar
    ser.reset_input_buffer()
    time.sleep(0.1)

    log(f"Enviando: {cmd}")
    time.sleep(0.2)

    # Enviar comando
    cmd_bytes = f"{cmd}\r".encode()
    ser.write(cmd_bytes)
    ser.flush()
    time.sleep(0.3)

    if wait_prompt:
        if cmd.startswith('load '):
            timeout = 60
        result, output = read_until(ser, ["BPI-R4>", "=>"], timeout=timeout)
        return result is not None, output
    return True, ""


def wait_for_uboot(ser, timeout=120):
    """Espera el prompt de U-Boot, interrumpiendo autoboot si es necesario"""
    log("Esperando U-Boot... (enciende o resetea el BPI-R4)")

    buffer = ""
    start = time.time()
    last_interrupt = 0

    while time.time() - start < timeout:
        if ser.in_waiting:
            try:
                chunk = ser.read(ser.in_waiting).decode('utf-8', errors='replace')
                buffer += chunk
                print(chunk, end='', flush=True)

                # Detectar countdown de autoboot
                if "Hit any key" in buffer or "autoboot" in buffer.lower():
                    log("Detectado autoboot, interrumpiendo...")
                    for _ in range(5):
                        ser.write(b" ")
                        time.sleep(0.05)
                    buffer = ""

                # Prompt de U-Boot detectado
                if "BPI-R4>" in buffer or "=>" in buffer:
                    log("Prompt de U-Boot detectado!")
                    time.sleep(0.3)
                    ser.reset_input_buffer()
                    return True

                # Detectar kernel panic
                if "Kernel panic" in buffer:
                    log("Detectado kernel panic - esperando reinicio...", "WARN")
                    buffer = ""

            except Exception as e:
                log(f"Error: {e}", "ERROR")
        else:
            # Enviar interrupciones periodicas
            now = time.time()
            if now - last_interrupt > 0.5:
                ser.write(b" ")
                last_interrupt = now
            time.sleep(0.1)

    return False


def main():
    parser = argparse.ArgumentParser(
        description='Automatizar boot de Armbian en BPI-R4',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  sudo python3 uboot_autoboot.py                    # Usar metodo rapido
  sudo python3 uboot_autoboot.py --manual           # Usar metodo manual completo
  sudo python3 uboot_autoboot.py -p /dev/ttyUSB1    # Puerto serial alternativo
        """
    )
    parser.add_argument('-p', '--port', default='/dev/ttyUSB0',
                        help='Puerto serial (default: /dev/ttyUSB0)')
    parser.add_argument('-b', '--baud', type=int, default=115200,
                        help='Baudrate (default: 115200)')
    parser.add_argument('-t', '--timeout', type=int, default=120,
                        help='Timeout para esperar U-Boot (default: 120s)')
    parser.add_argument('--manual', action='store_true',
                        help='Usar metodo manual (load kernel/initrd/dtb individualmente)')
    parser.add_argument('--no-wait', action='store_true',
                        help='No esperar U-Boot, asumir que ya esta en el prompt')
    args = parser.parse_args()

    # Seleccionar comandos
    commands = BOOT_COMMANDS_MANUAL if args.manual else BOOT_COMMANDS_SIMPLE

    log(f"Abriendo puerto {args.port} a {args.baud} baud...")

    try:
        ser = serial.Serial(
            port=args.port,
            baudrate=args.baud,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0.5,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False
        )
    except serial.SerialException as e:
        log(f"No se pudo abrir {args.port}: {e}", "ERROR")
        log("Intenta: sudo chmod 666 /dev/ttyUSB0", "ERROR")
        sys.exit(1)

    ser.reset_input_buffer()
    ser.reset_output_buffer()

    log("Puerto abierto correctamente")
    print("=" * 60)
    print("INSTRUCCIONES:")
    print("1. Si el BPI-R4 ya esta encendido, presiona el boton RESET")
    print("2. Si esta apagado, enciendelo ahora")
    print("3. El script detectara U-Boot y enviara los comandos")
    print("=" * 60)

    if args.no_wait:
        log("Modo directo - enviando comandos...")
        ser.write(b"\r")
        time.sleep(0.5)
    else:
        if not wait_for_uboot(ser, timeout=args.timeout):
            log("No se pudo obtener prompt de U-Boot", "ERROR")
            ser.close()
            sys.exit(1)

    # Enviar comandos de boot
    print("\n" + "=" * 60)
    log(f"Enviando {len(commands)} comandos de boot...")
    print("=" * 60 + "\n")

    for i, cmd in enumerate(commands):
        log(f"Comando {i+1}/{len(commands)}")

        # El ultimo comando no espera prompt (arranca Linux)
        is_last = (i == len(commands) - 1)
        is_boot_cmd = cmd.startswith('run ') or cmd.startswith('booti ')

        if is_last and is_boot_cmd:
            success, _ = send_command(ser, cmd, wait_prompt=False)
            log("Arrancando Linux... (Ctrl+C para salir)")
            try:
                while True:
                    if ser.in_waiting:
                        chunk = ser.read(ser.in_waiting).decode('utf-8', errors='replace')
                        print(chunk, end='', flush=True)
                    time.sleep(0.05)
            except KeyboardInterrupt:
                log("\nInterrumpido por usuario")
        else:
            success, output = send_command(ser, cmd, wait_prompt=True, timeout=60)
            if not success:
                log("Comando timeout o fallo", "WARN")
        time.sleep(0.2)

    ser.close()
    log("Completado")


if __name__ == "__main__":
    main()
