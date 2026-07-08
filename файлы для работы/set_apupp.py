"""Переключение sisd на apupp."""

import serial
import apupp, sisd


def run() -> None:
    """Выполнение скрипта."""
    try:
        print('Переключение sisd на АПУПП.')
        apu_sisd = sisd.Sisd()
        apu_sisd.change_to_apupp()
    except (ValueError, IndexError, serial.SerialException):
        apu_apupp = apupp.Apupp()
        apu_apupp.disconnect()
        print('Пульт АПУ-ЦВМ12Р уже в режиме обмена данными по АПУПП.')
    else:
        print('Готово')


if __name__ == '__main__':
    run(test_name='Переключение sisd на АПУПП.')
