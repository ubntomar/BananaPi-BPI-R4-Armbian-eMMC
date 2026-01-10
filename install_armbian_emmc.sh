#!/bin/sh
# Script para instalar Armbian en eMMC del BPI-R4
# Ejecutar desde OpenWrt corriendo en NAND

set -e

echo "=== Instalacion de Armbian en eMMC del BPI-R4 ==="
echo ""

# Verificar que los archivos existen
if [ ! -f /tmp/bpi-r4_emmc_bl2.img ]; then
    echo "ERROR: No se encuentra /tmp/bpi-r4_emmc_bl2.img"
    exit 1
fi

if [ ! -f /tmp/bpi-r4_emmc_fip.bin ]; then
    echo "ERROR: No se encuentra /tmp/bpi-r4_emmc_fip.bin"
    exit 1
fi

if [ ! -f /tmp/armbian-bpi-r4.img ]; then
    echo "ERROR: No se encuentra /tmp/armbian-bpi-r4.img"
    exit 1
fi

# Verificar que mmcblk0 existe (eMMC)
if [ ! -b /dev/mmcblk0 ]; then
    echo "ERROR: No se encuentra /dev/mmcblk0 (eMMC)"
    exit 1
fi

echo "Archivos encontrados:"
ls -lh /tmp/bpi-r4_emmc_bl2.img /tmp/bpi-r4_emmc_fip.bin /tmp/armbian-bpi-r4.img
echo ""

echo "ADVERTENCIA: Esto borrara TODO el contenido de la eMMC!"
echo "Presiona ENTER para continuar o Ctrl+C para cancelar..."
read dummy

echo ""
echo "[1/4] Desbloqueando particion boot0 de eMMC..."
echo 0 > /sys/block/mmcblk0boot0/force_ro

echo "[2/4] Escribiendo BL2 en mmcblk0boot0..."
dd if=/tmp/bpi-r4_emmc_bl2.img of=/dev/mmcblk0boot0 status=progress

echo "[3/4] Escribiendo imagen Armbian en eMMC..."
dd if=/tmp/armbian-bpi-r4.img of=/dev/mmcblk0 bs=1M status=progress conv=fsync

echo "[4/4] Escribiendo FIP en particion 4..."
# Esperar a que las particiones se detecten
sync
sleep 2
partprobe /dev/mmcblk0 2>/dev/null || true
sleep 1

if [ -b /dev/mmcblk0p4 ]; then
    dd if=/tmp/bpi-r4_emmc_fip.bin of=/dev/mmcblk0p4 status=progress
else
    echo "NOTA: Particion mmcblk0p4 no encontrada, escribiendo FIP en offset"
    dd if=/tmp/bpi-r4_emmc_fip.bin of=/dev/mmcblk0 bs=512 seek=13312 conv=notrunc
fi

echo ""
echo "[5/5] Habilitando boot desde eMMC..."
mmc bootpart enable 1 1 /dev/mmcblk0

sync

echo ""
echo "=== INSTALACION COMPLETADA ==="
echo ""
echo "Ahora:"
echo "1. Apaga el BPI-R4"
echo "2. Cambia el DIP switch para arrancar desde eMMC:"
echo "   SW3-A = 1 (ON)"
echo "   SW3-B = 0 (OFF)"
echo "3. Enciende el BPI-R4"
echo ""
echo "Usuario por defecto de Armbian: root"
echo "Contrasena: 1234 (te pedira cambiarla en el primer login)"
echo ""
