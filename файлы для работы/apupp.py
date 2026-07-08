"""Модуль для работы с АПУ-ЦВМ12Р через программный протокол APUPP."""

from __future__ import annotations

import enum
from dataclasses import dataclass
from types import MappingProxyType
from config import PORT, BAUDRATE

import serial


CONNECT_COUNT = 1024  # Кол-во повторений команды connect для установления связи по APUPP (из RE)


@enum.unique
class FieldName(enum.Enum):
    """Имена полей команд протокола."""

    CMD = 'CMD'
    RES = 'RES'
    SVK = 'SVK'
    DATA = 'DATA'
    TYPE = 'TYPE'
    ADDR = 'ADDR'
    RXD = 'RXD'
    TXD = 'TXD'
    ID = 'ID'
    COUNT = 'COUNT'
    FIND = 'FIND'
    T = 'T'


class FieldValue:
    """Значение поля команды, либо результата команды."""

    def __init__(self, value: int | list[int] | bytes) -> None:
        """Конструктор класса.

        Args:
            value: изначальное значение поля

        Raises:
            ValueError: если передан недопустимый тип аргумента

        """
        if isinstance(value, int):
            self.bytes_value = _int_to_bytes(value)
        elif isinstance(value, list):
            self.bytes_value = _list_to_bytes(value)
        elif isinstance(value, bytes):
            self.bytes_value = value
        else:
            msg = 'Допустимые типы данных: int | list[int] | bytes'
            raise TypeError(msg)

    def get_int_value(self) -> int:
        """Возвращает значение поля в виде int.

        Returns:
            Значение поля в int

        """
        return _bytes_to_int(self.bytes_value)

    def get_list_value(self) -> list[int]:
        """Возвращает значение поля в виде списка битов.

        Returns:
            Значение поля в виде списка битов

        """
        return _bytes_to_list(self.bytes_value)

    def get_reversed_field(self) -> FieldValue:
        """Возвращает значение поля в Little Endian.

        Returns:
            Значение поля в Little Endian

        """
        return FieldValue(self.bytes_value[::-1])


def _list_to_bytes(bit_array: list[int]) -> bytes:
    """Преобразование массива битов в bytes.

    Args:
        bit_array: значение в виде списка битов.

    Returns:
        Значение в формате bytes.
    """
    # Вычисляем, сколько нулей нужно добавить
    remainder = len(bit_array) % 8
    padding = 0 if remainder == 0 else 8 - remainder

    # Создаём новый список с дополнением нулями
    padded_bits = [0 for _ in range(padding)]
    padded_bits.extend(bit_array)

    # Разбиваем на группы по 8 бит и преобразуем каждую группу в число
    byte_array = []
    for i in range(0, len(padded_bits), 8):
        byte_str = ''.join(map(str, padded_bits[i : i + 8]))
        byte_value = int(byte_str, 2)
        byte_array.append(byte_value)

    # Преобразуем список чисел в объект bytes
    return bytes(byte_array)


def _int_to_bytes(int_data: int) -> bytes:
    """Преобразование int в bytes.

    Args:
        int_data: значение в int

    Returns:
        Значение в bytes

    """
    byte_length = (int_data.bit_length() + 7) // 8 if int_data.bit_length() > 0 else 1
    return int_data.to_bytes(byte_length, byteorder='big')


def _bytes_to_list(byte_data: bytes) -> list[int]:
    """Преобразование bytes в список битов.

    Args:
        byte_data: значение в bytes

    Returns:
        Значение в виде списка битов

    """
    bits = []
    for byte in byte_data:
        bits.extend([int(bit) for bit in f'{byte:08b}'])
    return bits


def _bytes_to_int(byte_data: bytes) -> int:
    """Преобразование bytes в int.

    Args:
        byte_data: значение в bytes

    Returns:
        Значение в int

    """
    return int.from_bytes(byte_data, byteorder='big')


@enum.unique
class Svk(enum.IntEnum):
    """Выбранный ВК."""

    VK1 = 0x0
    VK2 = 0x1

    def __str__(self):
        """Переопределение магического метода для сторокового отображения объекта."""
        if self.value == 0:
            return '1'
        return '2'


@enum.unique
class SystemControl(enum.IntEnum):
    """Системные команды для управления АПУ-ЦВМ12Р."""

    CONNECT = 0x0  # Установка соединения
    DISCONNECT = 0x1  # Сброс соединения
    GET_VERSION = 0x2  # Получение версии АПУ-ЦВМ12Р
    ON_DEBUG = 0x3  # Включение режима отладки
    ERASE_EEPROM = 0x4  # Стереть ЭНПЗУ
    LOAD_LED_VALUE = 0x5  # Загрузка исходных состояний светодиодов панели АПУ-ЦВМ12Р
    OFF_AUTO_LOAD = 0x6  # Выключение автозагрузки состояний КПУ и ТК ВК1 и ВК2
    ON_AUTO_LOAD = 0x7  # Включение автозагрузки состояний КПУ и ТК ВК1 и ВК2
    WR_TSCONF = 0x8  # Запись нового значения в регистр конфигурации термодатчиков TSCONF
    RD_TSCONF = 0x9  # Чтение текущего значения регистра конфигурации термодатчиков TSCONF


@enum.unique
class LedControl(enum.IntEnum):
    """Команды для управления светодиодами панели АПУ-ЦВМ12Р."""

    WR_KPUL = 0x10  # Запись нового состояния светодиодов КПУ ВК1 и ВК2
    RD_KPUL = 0x11  # Получение текущего состояния светодиодов КПУ ВК1 и ВК2
    WR_KKSL = 0x12  # Запись нового состояния светодиодов ККС ВК1 и ВК2
    RD_KKSL = 0x13  # Получение текущего состояния светодиодов ККС ВК1 и ВК2
    WR_TELEML = 0x14  # Запись нового состояния светодиодов телеметрии ВК1 и ВК2
    RD_TELEML = 0x15  # Получение текущего состояния светодиодов телеметрии ВК1 и ВК2
    WR_PRL = 0x16  # Запись нового состояния светодиодов прерывания ВК1 и ВК2
    RD_PRL = 0x17  # Получение текущего состояния светодиодов прерывания ВК1 и ВК2


@enum.unique
class ButtonControl(enum.IntEnum):
    """Команды для управления кнопками АПУ-ЦВМ12Р."""

    GET_KPUB = 0x20  # Получение текущего состояния кнопок КПУ ВК1 и ВК2
    GET_TKB = 0x21  # Получение текущего состояния кнопок ТК ВК1 и ВК2
    GET_PRB = 0x22  # Получение текущего состояния кнопок генерации прерывания прерываний ВК1 и ВК2
    OFF_TRACK_KPUB = 0x24  # Отключение отслеживание изменений состояний кнопок КПУ ВК1 и ВК2
    ON_TRACK_KPUB = 0x25  # Включение отслеживание изменений состояний кнопок КПУ ВК1 и ВК2
    OFF_TRACK_TKB = 0x26  # Отключение отслеживание изменений состояний кнопок ТК ВК1 и ВК2
    ON_TRACK_TKB = 0x27  # Включение отслеживание изменений состояний кнопок ТК ВК1 и ВК2
    OFF_TRACK_PRB = 0x28  # Отключение отслеживание изменений состояний кнопок генерации прерывания ВК1 и ВК2
    ON_TRACK_PRB = 0x29  # Включение отслеживание изменений состояний кнопок генерации прерывания ВК1 и ВК2


@enum.unique
class TelemetryControl(enum.IntEnum):
    """Команды для управления телеметрией АПУ-ЦВМ12Р."""

    GET_KKS = 0x30  # Получение текущего состояния сигналов ККС ВК1 и ВК2
    GET_PVP = 0x31  # Получение текущего состояния сигналов признаков вторичного питания ВК1 и ВК2
    OFF_TRACK_KKS = 0x32  # Отключение отслеживание изменений состояний сигналов ККС ВК1 и ВК2
    ON_TRACK_KKS = 0x33  # Включение отслеживание изменений состояний сигналов ККС ВК1 и ВК2
    OFF_TRACK_PVP = 0x34  # Отключение отслеживание изменений сигналов признаков вторичного питания ВК1 и ВК2
    ON_TRACK_PVP = 0x35  # Включение отслеживания изменений сигналов признаков вторичного питания ВК1 и ВК2


@enum.unique
class KpuTkControl(enum.IntEnum):
    """Команды для управления КПУ и ТК АПУ-ЦВМ12Р."""

    WR_KPU = 0x40  # Запись нового состояния КПУ ВК1 и ВК2
    RD_KPU = 0x41  # Чтение текущего состояния КПУ ВК1 и ВК2
    OFF_TRACK_KPU = 0x42  # Отключение отслеживание изменений состояний сигналов КПУ ВК1 и ВК2
    ON_TRACK_KPU = 0x43  # Включение отслеживание изменений состояний сигналов КПУ ВК1 и ВК2
    CHANGE_TK = 0x44  # Изменение состояний ТК ВК1 и ВК2
    GET_TK = 0x45  # Получение текущих состояний ТК ВК1 и ВК2
    OFF_TRACK_TK = 0x46  # Выключение отслеживания изменения состояния ТК ВК1 и ВК2
    ON_TRACK_TK = 0x47  # Включение отслеживания изменения состояния ТК ВК1 и ВК2


@enum.unique
class KsControl(enum.IntEnum):
    """Команды для управления КC АПУ-ЦВМ12Р."""

    WR_GP_PARAM = 0x50  # Запись нового значения параметра генерации сигнала КС ВК1 и ВК2
    RD_GP_PARAM = 0x51  # Чтение текущего значения параметра генерации сигнала КС ВК1 и ВК2
    WR_GP_MODE = 0x52  # Запись нового значения режимов работы генераторов импульсов ВК1 и ВК2
    RD_GP_MODE = 0x53  # Чтение текущего значения режимов работы генераторов импульсов ВК1 и ВК2
    WR_GP_ETRANS = 0x54  # Запись нового значения в регистр включения генераторов импульсов ВК1 и ВК2
    RD_GP_ETRANS = 0x55  # Чтение текущего значения регистра включения генераторов импульсов ВК1 и ВК2
    RUN_GP = 0x56  # Запуск генераторов импульсов ВК1 и ВК2
    GET_GP_PRD = 0x57  # Чтение значения флагов завершения очередного импульса ВК1 и ВК2
    GET_GP_STP = 0x58  # Чтение значения флагов остановленных генераторов импульсов ВК1 и ВК2
    GET_GP_PRD_CT = 0x59  # Чтение значения кол-ва пройденных периодов генерации импульса ген. импульсов ВК1 и ВК2
    OFF_TRACK_GP_PRD = 0x5A  # Отключить отслеживание значений флагов завершения очередного импульса ВК1 и ВК2
    ON_TRACK_GP_PRD = 0x5B  # Включить отслеживание значений флагов завершения очередного импульса ВК1 и ВК2
    OFF_TRACK_GP_STP = 0x5C  # Отключить отслеживание значений флагов остановленных генераторов импульсов ВК1 и ВК2
    ON_TRACK_GP_STP = 0x5D  # Включить отслеживание значений флагов остановленных генераторов импульсов ВК1 и ВК2


@enum.unique
class EnpzuControl(enum.IntEnum):
    """Команды для управления ЭНПЗУ АПУ-ЦВМ12Р."""

    WR_EEPROM = 0x60  # Запись данных в ЭНПЗУ
    RD_EEPROM = 0x61  # Чтение данных из ЭНПЗУ
    RD_STS_EEPROM = 0x62  # Чтение статусного регистра ЭНПЗУ


@enum.unique
class OneWireControl(enum.IntEnum):
    """Команды для управления контроллерами 1-Wire АПУ-ЦВМ12Р."""

    WR_OW_REG = 0x70  # Запись нового значения в управляющий регистр контроллеров 1-Wire ВК1 и ВК2
    RD_OW_REG = 0x71  # Чтение текущего значения управляющего регистра контроллеров 1-Wire ВК1 и ВК2


@enum.unique
class UartControl(enum.IntEnum):
    """Команды для управления контроллерами UART АПУ-ЦВМ12Р."""

    WR_UART_REG = 0x80  # Запись нового значения в управляющий регистр контроллеров UART
    RD_UART_REG = 0x81  # Чтение текущего значения управляющего регистра контроллеров UART


@enum.unique
class MatrixControl(enum.IntEnum):
    """Команды для управления матричным коммутатором АПУ-ЦВМ12Р."""

    CONNECT_RX_TX = 0x90  # Подключение линии приема данных RXD к линии передачи данных TXD
    DISCONNECT_TX = 0x91  # Отключение линии передачи данных TXD
    WR_DEFVAL = 0x92  # Запись новых значений по умолчанию линий передачи данных TXD
    RD_DEFVAL = 0x93  # Чтение текущих значений по умолчанию линий передачи данных TXD
    GET_RX = 0x94  # Получение текущей линии приема данных RXD у линии передачи данных TXD


@enum.unique
class ThermalSensorControl(enum.IntEnum):
    """Команды для управления термодатчиками ВК1 и ВК2 АПУ-ЦВМ12Р."""

    SEARCH_TS = 0xA0  # Поиск идентификаторов термодатчиков ВК1 и ВК2
    GET_IDS_TS = 0xA1  # Получение идентификаторов термодатчиков ВК1 и ВК2
    MEASURE_TEMP = 0xA2  # Запуск измерения температуры термодатчиками ВК1 и ВК2
    GET_TEMP = 0xA3  # Получение измеренной температуры термодатчиками ВК1 и ВК2
    MEASURE_TEMP_ID = 0xA4  # Запуск измерения температуры определенным термодатчика ВК1 и ВК2
    GET_TEMP_ID = 0xA5  # Получение измеренной температуры определенного термодатчика ВК1 и ВК2


@enum.unique
class TimerControl(enum.IntEnum):
    """Команды для управления термодатчиками ВК1 и ВК2 АПУ-ЦВМ12Р."""

    WR_WCNT = 0xB0  # Запись нового значения в регистр WCNT
    RD_WCNT = 0xB1  # Чтение текущего значения регистра WCNT
    RD_RCNT = 0xB2  # Чтение текущего значения регистра RCNT
    RUN_TMR = 0xB3  # Запуск таймера
    RST_TMR = 0xB4  # Сброс таймера
    CHECK_TMR = 0xB5  # Проверка таймера
    OFF_TRACK_TMR = 0xB6  # Отключить отслеживание таймера
    ON_TRACK_TMR = 0xB7  # Включить отслеживание таймера


COMMAND_DESCRIPTION = MappingProxyType(
    {
        SystemControl.CONNECT: 'Установка соединения',
        SystemControl.DISCONNECT: 'Сброс соединения',
        SystemControl.GET_VERSION: 'Получение версии АПУ-ЦВМ12Р',
        SystemControl.ON_DEBUG: 'Включение режима отладки',
        SystemControl.ERASE_EEPROM: 'Стереть ЭНПЗУ',
        SystemControl.LOAD_LED_VALUE: 'Загрузка исходных состояний светодиодов панели АПУ-ЦВМ12Р',
        SystemControl.OFF_AUTO_LOAD: 'Выключение автозагрузки состояний КПУ и ТК ВК1 и ВК2',
        SystemControl.ON_AUTO_LOAD: 'Включение автозагрузки состояний КПУ и ТК ВК1 и ВК2',
        SystemControl.WR_TSCONF: 'Запись нового значения в регистр конфигурации термодатчиков TSCONF',
        SystemControl.RD_TSCONF: 'Чтение текущего значения регистра конфигурации термодатчиков TSCONF',
        LedControl.WR_KPUL: 'Запись новых состояний светодиодов КПУ ВК1 и ВК2',
        LedControl.RD_KPUL: 'Чтение текущих состояний светодиодов КПУ ВК1 и ВК2',
        LedControl.WR_KKSL: 'Запись новых состояний светодиодов ККС ВК1 и ВК2',
        LedControl.RD_KKSL: 'Чтение текущих состояний светодиодов ККС ВК1 и ВК2',
        LedControl.WR_TELEML: 'Запись новых состояний светодиодов телеметрии ВК1 и ВК2',
        LedControl.RD_TELEML: 'Чтение текущих состояний светодиодов телеметрии ВК1 и ВК2',
        LedControl.WR_PRL: 'Запись новых состояний светодиодов прерывания ВК1 и ВК2',
        LedControl.RD_PRL: 'Чтение текущих состояний светодиодов прерывания ВК1 и ВК2',
        ButtonControl.GET_KPUB: 'Получение текущих состояний кнопок КПУ ВК1 и ВК2',
        ButtonControl.GET_TKB: 'Получение текущих состояний кнопок смены ТК ВК1 и ВК2',
        ButtonControl.GET_PRB: 'Получение текущих состояний кнопок генерации прерывания ВК1 и ВК2',
        ButtonControl.OFF_TRACK_KPUB: 'Выключение отслеживания изменений состояний кнопок КПУ ВК1 и ВК2',
        ButtonControl.ON_TRACK_KPUB: 'Включение отслеживания изменений состояний кнопок КПУ ВК1 и ВК2',
        ButtonControl.OFF_TRACK_TKB: 'Выключение отслеживания изменений состояний кнопок смены ТК ВК1 и ВК2',
        ButtonControl.ON_TRACK_TKB: 'Включение отслеживания изменений состояний кнопок смены ТК ВК1 и ВК2',
        ButtonControl.OFF_TRACK_PRB: (
            'Выключение отслеживания изменений состояний кнопок генерации прерывания ВК1 и ВК2'
        ),
        ButtonControl.ON_TRACK_PRB: 'Включение отслеживания изменений состояний кнопок генерации прерывания ВК1 и ВК2',
        TelemetryControl.GET_KKS: 'Получение текущих состояний сигналов ККС ВК1 и ВК2',
        TelemetryControl.GET_PVP: 'Получение текущих состояний сигналов признаков вторичного питания ВК1 и ВК2',
        TelemetryControl.OFF_TRACK_KKS: 'Выключение отслеживания изменений состояний сигналов ККС ВК1 и ВК2',
        TelemetryControl.ON_TRACK_KKS: 'Включение отслеживания изменений состояний сигналов ККС ВК1 и ВК2',
        TelemetryControl.OFF_TRACK_PVP: (
            'Выключение отслеживания изменений сигналов признаков вторичного питания ВК1 и ВК2'
        ),
        TelemetryControl.ON_TRACK_PVP: (
            'Включение отслеживания изменений сигналов признаков вторичного питания ВК1 и ВК2'
        ),
        KpuTkControl.WR_KPU: 'Запись новых состояний сигналов КПУ ВК1 и ВК2',
        KpuTkControl.RD_KPU: 'Чтение текущих состояний сигналов КПУ ВК1 и ВК2',
        KpuTkControl.OFF_TRACK_KPU: 'Выключение отслеживания изменений состояний сигналов КПУ ВК1 и ВК2',
        KpuTkControl.ON_TRACK_KPU: 'Включение отслеживания изменений состояний сигналов КПУ ВК1 и ВК2',
        KpuTkControl.CHANGE_TK: 'Изменение состояний ТК ВК1 и ВК2',
        KpuTkControl.GET_TK: 'Получение текущих состояний ТК ВК1 и ВК2',
        KpuTkControl.OFF_TRACK_TK: 'Выключение отслеживания изменения состояния ТК ВК1 и ВК2',
        KpuTkControl.ON_TRACK_TK: 'Включение отслеживания изменения состояния ТК ВК1 и ВК2',
        KsControl.WR_GP_PARAM: 'Запись нового значения параметра генерации сигнала КС ВК1 и ВК2',
        KsControl.RD_GP_PARAM: 'Чтение текущего значения параметра генерации сигнала КС ВК1 и ВК2',
        KsControl.WR_GP_MODE: 'Запись нового значения режимов работы генераторов импульсов ВК1 и ВК2',
        KsControl.RD_GP_MODE: 'Чтение текущего значения режимов работы генераторов импульсов ВК1 и ВК2',
        KsControl.WR_GP_ETRANS: 'Запись нового значения в регистр включения генераторов импульсов ВК1 и ВК2',
        KsControl.RD_GP_ETRANS: 'Чтение текущего значения регистра включения генераторов импульсов ВК1 и ВК2',
        KsControl.RUN_GP: 'Запуск генераторов импульсов ВК1 и ВК2',
        KsControl.GET_GP_PRD: (
            'Получение последних сохранённых значений флагов завершения очередного импульса ВК1 и ВК2'
        ),
        KsControl.GET_GP_STP: 'Получение значений флагов остановленных генераторов импульсов ВК1 и ВК2',
        KsControl.GET_GP_PRD_CT: (
            'Получение значения количества пройденных периодов генерации импульса генераторов импульсов ВК1 и ВК2'
        ),
        KsControl.OFF_TRACK_GP_PRD: 'Выключить отслеживание значений флагов завершения очередного импульса ВК1 и ВК2',
        KsControl.ON_TRACK_GP_PRD: 'Включить отслеживание значений флагов завершения очередного импульса ВК1 и ВК2',
        KsControl.OFF_TRACK_GP_STP: (
            'Выключить отслеживание значений флагов остановленных генераторов импульсов ВК1 и ВК2'
        ),
        KsControl.ON_TRACK_GP_STP: (
            'Включить отслеживание значений флагов остановленных генераторов импульсов ВК1 и ВК2'
        ),
        EnpzuControl.WR_EEPROM: 'Запись данных в ЭНПЗУ',
        EnpzuControl.RD_EEPROM: 'Чтение данных из ЭНПЗУ',
        EnpzuControl.RD_STS_EEPROM: 'Чтение статусного регистра ЭНПЗУ',
        OneWireControl.WR_OW_REG: 'Запись нового значения в управляющий регистр контроллеров 1-Wire ВК1 и ВК2',
        OneWireControl.RD_OW_REG: 'Чтение текущего значения управляющего регистра контроллеров 1-Wire ВК1 и ВК2',
        UartControl.WR_UART_REG: 'Запись нового значения в управляющий регистр контроллера UART-0',
        UartControl.RD_UART_REG: 'Чтение текущего значения управляющего регистра контроллера UART-0',
        MatrixControl.CONNECT_RX_TX: 'Подключение линии приема данных RXD к линии передачи данных TXD',
        MatrixControl.DISCONNECT_TX: 'Отключение линии передачи данных TXD',
        MatrixControl.WR_DEFVAL: 'Запись новых значений по умолчанию линий передачи данных TXD',
        MatrixControl.RD_DEFVAL: 'Чтение текущих значений по умолчанию линий передачи данных TXD',
        MatrixControl.GET_RX: 'Получение текущей линии приема данных RXD у линии передачи данных TXD',
        ThermalSensorControl.SEARCH_TS: 'Поиск идентификаторов термодатчиков ВК1 и ВК2',
        ThermalSensorControl.GET_IDS_TS: 'Получение идентификаторов термодатчиков ВК1 и ВК2',
        ThermalSensorControl.MEASURE_TEMP: 'Запуск измерения температуры термодатчиками ВК1 и ВК2',
        ThermalSensorControl.GET_TEMP: 'Получение измеренной температуры термодатчиками ВК1 и ВК2',
        ThermalSensorControl.MEASURE_TEMP_ID: 'Запуск измерения температуры определенным термодатчика ВК1 и ВК2',
        ThermalSensorControl.GET_TEMP_ID: 'Получение измеренной температуры определенного термодатчика ВК1 и ВК2',
        TimerControl.WR_WCNT: 'Запись нового значения в регистр WCNT',
        TimerControl.RD_WCNT: 'Чтение текущего значения регистра WCNT',
        TimerControl.RD_RCNT: 'Чтение текущего значения регистра RCNT',
        TimerControl.RUN_TMR: 'Запуск таймера',
        TimerControl.RST_TMR: 'Сброс таймера',
        TimerControl.CHECK_TMR: 'Проверка таймера',
        TimerControl.OFF_TRACK_TMR: 'Отключить отслеживание таймера',
        TimerControl.ON_TRACK_TMR: 'Включить отслеживание таймера',
    },
)


@enum.unique
class TypeGpParam(enum.IntEnum):
    """Возможные значения поля TYPE для команд wr_gp_param и rd_gp_param."""

    CPUL1 = 0x0  # количество генерируемых импульсов CPUL*1 сигнала метки времени №1
    CPUL2 = 0x1  # количество генерируемых импульсов CPUL*2 сигнала метки времени №2
    CPUL3 = 0x2  # количество генерируемых импульсов CPUL*3 сигнала прерывания
    PER1 = 0x10  # длительность периода PER*1 сигнала метки времени №1
    PER2 = 0x11  # длительность периода PER*2 сигнала метки времени №2
    PER3 = 0x12  # длительность периода PER*3 сигнала прерывания
    DUT1 = 0x20  # длительность активного уровня DUT*1 сигнала метки времени №1
    DUT2 = 0x21  # длительность активного уровня DUT*2 сигнала метки времени №2
    DUT3 = 0x22  # длительность активного уровня DUT*3 сигнала прерывания


@enum.unique
class TypeGetGpPrdCt(enum.IntEnum):
    """Возможные значения поля TYPE для команды get_gp_prd_ct."""

    CPER1 = 0x0  # количество пройденных периодов генерации импульсов CPER*1 сигнала метки времени №1
    CPER2 = 0x1  # количество пройденных периодов генерации импульсов CPER *2 сигнала метки времени №2
    CPER3 = 0x2  # количество пройденных периодов генерации импульсов CPER *3 сигнала прерывания


@enum.unique
class TypeWrOwReg(enum.IntEnum):
    """Возможные значения поля TYPE для команды wr_ow_reg."""

    WR_CMD_REG = 0x0  # запись регистра команды
    WR_TRANSFER_REG = 0x1  # запись передающего регистра
    WR_PRD_REG = 0x2  # запись регистра прерывания
    WR_TRACK_PRD = 0x3  # запись регистра разрешения прерываний
    WR_DIVIDER_REG = 0x4  # запись регистра делителя частоты
    WR_CONTROL_REG = 0x5  # запись регистра управления


@enum.unique
class TypeRdOwReg(enum.IntEnum):
    """Возможные значения поля TYPE для команды rd_ow_reg."""

    RD_CMD_REG = 0x0  # чтение регистра команды
    RD_RECEIVING_REG = 0x1  # чтение принимающего регистра
    RD_PRD_REG = 0x2  # чтение регистра прерывания
    RD_TRACK_PRD = 0x3  # чтение регистра разрешения прерываний
    RD_DIVIDER_REG = 0x4  # чтение регистра делителя частоты
    RD_CONTROL_REG = 0x5  # чтение регистра управления


@enum.unique
class TypeWrUartReg(enum.IntEnum):
    """Возможные значения поля TYPE для команды wr_uart_reg."""

    WR_THR_DLL = 0x0  # запись регистра THR, если включена косвенная адресация, то запись регистра DLL
    WR_IER_DLM = 0x1  # запись регистра IER, если включена косвенная адресация, то запись регистра DLM
    WR_FCR = 0x2  # запись регистра FCR
    WR_LCR = 0x3  # запись регистра LCR
    WR_MCR = 0x4  # запись регистра MCR


@enum.unique
class TypeRdUartReg(enum.IntEnum):
    """Возможные значения поля TYPE для команды rd_uart_reg."""

    RD_RHR_DLL = 0x0  # чтение регистра RHR, если включена косвенная адресация, то чтение регистра DLL
    RD_IER_DLM = 0x1  # чтение регистра IER, если включена косвенная адресация, то чтение регистра DLM
    RD_ISR = 0x2  # чтение регистра ISR
    RD_LCR = 0x3  # чтения регистра LCR
    RD_MCR = 0x4  # чтения регистра MCR
    RD_LSR = 0x5  # чтения регистра LSR


@enum.unique
class TypeMatrixTXD(enum.IntEnum):
    """Возможные значения идентификаторов линии передачи данных TXD."""

    TXD1 = 0x1  # идентификатор линии передачи данных TXD1
    TXD2 = 0x2  # идентификатор линии передачи данных TXD2
    TXD3 = 0x4  # идентификатор линии передачи данных TXD3
    TXD4 = 0x8  # идентификатор линии передачи данных TXD4
    TXD5 = 0x10  # идентификатор линии передачи данных TXD5
    TXD6 = 0x20  # идентификатор линии передачи данных TXD6
    TXD7 = 0x40  # идентификатор линии передачи данных TXD7


@enum.unique
class TypeMatrixRXD(enum.IntEnum):
    """Возможные значения идентификаторов линии передачи данных RXD."""

    RXD1 = 0x1  # идентификатор линии передачи данных RXD1
    RXD2 = 0x2  # идентификатор линии передачи данных RXD2
    RXD3 = 0x4  # идентификатор линии передачи данных RXD3
    RXD4 = 0x8  # идентификатор линии передачи данных RXD4
    RXD5 = 0x10  # идентификатор линии передачи данных RXD5
    RXD6 = 0x20  # идентификатор линии передачи данных RXD6
    RXD7 = 0x40  # идентификатор линии передачи данных RXD7


@enum.unique
class TypeTemp(enum.IntEnum):
    """Возможные значения поля TYPE для команд управления термодатчиками."""

    RANGE1 = 0x0  # диапазон памяти 1
    RANGE2 = 0x1  # диапазон памяти 2


@enum.unique
class TypeTmr(enum.IntEnum):
    """Возможные значения поля TYPE для команд управления таймерами."""

    TMR0 = 0x0  # выбирает таймер-0
    TMR1 = 0x1  # выбирает таймер-1


@enum.unique
class CommandMode(enum.IntEnum):
    """Режимы работы для команд включения/выключения."""

    OFF = 0
    ON = 1


class ApuppError(Exception):
    """Базовый класс, для исключений при работе по АПУПП с АПУ-ЦВМ12Р."""


class SerialResultError(ApuppError):
    """Исключение, выбрасываемое, когда кол-во байт результата не совпадает с ожидаемым."""


class ArgumentSizeError(ApuppError):
    """Исключение, выбрасываемое, когда кол-во байт переданного аргумента не совпадает с ожидаемым для этой функции."""


@dataclass
class CommandField:
    """Класс для полей команды (используется для составления команд в _execute_command)."""

    name: FieldName
    value: FieldValue
    size: int


@dataclass
class ResultField:
    """Класс для полей результата (используется для составления команд в _execute_command)."""

    name: FieldName
    size: int


@dataclass
class ReadResultField:
    """Класс для полей, которые являются результатом работы команды."""

    name: FieldName
    value: FieldValue


class Apupp:  # noqa: WPS214
    """Модуль для работы с АПУ-ЦВМ12Р через программный протокол APUPP."""

    def __init__(self):
        """Конструктор класса. Открывает соединение по COM-порту с АПУ."""
        self._connection = serial.Serial(
            port=PORT,
            baudrate=BAUDRATE,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_TWO,
            timeout=10,
        )
        self.connect()

    def __del__(self):  # noqa: WPS603
        """Деструктор класса."""
        self._connection.close()

    """ # noqa: WPS428, WPS462
    Системные команды
    """

    def connect(self) -> None:
        """Установка соединения."""
        self._execute_command(
            cmd_fields=(CommandField(name=FieldName.CMD, value=FieldValue(SystemControl.CONNECT), size=1),),
            result_fields=(ResultField(name=FieldName.RES, size=1),),  # noqa: WPS204
        )

    def disconnect(self) -> None:
        """Сброс соединения."""
        self._execute_command(
            cmd_fields=(CommandField(name=FieldName.CMD, value=FieldValue(SystemControl.DISCONNECT), size=1),),
            result_fields=(ResultField(name=FieldName.RES, size=1),),
        )

    def get_version(self) -> FieldValue:
        """Получение версии АПУ-ЦВМ12Р.

        Returns:
            Полученная версия прошивки ПЛИС пульта АПУ-ЦВМ12Р

        """
        result = self._execute_command(
            cmd_fields=(CommandField(name=FieldName.CMD, value=FieldValue(SystemControl.GET_VERSION), size=1),),
            result_fields=(ResultField(name=FieldName.RES, size=1), ResultField(name=FieldName.DATA, size=4)),
        )
        return next(field.value for field in result if field.name is FieldName.DATA)

    def on_debug(self) -> None:
        """Включение режима отладки. Режим отладки это работа по протоколу sisd."""
        self._execute_command(
            cmd_fields=(CommandField(name=FieldName.CMD, value=FieldValue(SystemControl.ON_DEBUG), size=1),),
            result_fields=(ResultField(name=FieldName.RES, size=1),),
        )

    def erase_eeprom(self) -> None:
        """Стереть ЭНПЗУ."""
        self._execute_command(
            cmd_fields=(CommandField(name=FieldName.CMD, value=FieldValue(SystemControl.ERASE_EEPROM), size=1),),
            result_fields=(ResultField(name=FieldName.RES, size=1),),
        )

    def load_led_value(self) -> None:
        """Загрузка исходных состояний светодиодов панели АПУ-ЦВМ12Р."""
        self._execute_command(
            cmd_fields=(CommandField(name=FieldName.CMD, value=FieldValue(SystemControl.LOAD_LED_VALUE), size=1),),
            result_fields=(ResultField(name=FieldName.RES, size=1),),
        )

    def auto_load(self, mode: CommandMode) -> None:
        """Включение/выключение автозагрузки состояний КПУ и ТК ВК1 и ВК2.

        Args:
            mode: режим (включение/выключение)

        """
        cmd = SystemControl.ON_AUTO_LOAD if mode else SystemControl.OFF_AUTO_LOAD  # noqa: WPS204
        self._execute_command(
            cmd_fields=(CommandField(name=FieldName.CMD, value=FieldValue(cmd), size=1),),  # noqa: WPS204
            result_fields=(ResultField(name=FieldName.RES, size=1),),
        )

    def wr_tsconf(self, data: FieldValue) -> None:
        """Запись нового значения в регистр конфигурации термодатчиков TSCONF.

        Args:
            data: новое значение для записи

        """
        self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(SystemControl.WR_TSCONF), size=1),
                CommandField(name=FieldName.DATA, value=data, size=1),  # noqa: WPS204
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.DATA, size=1),  # noqa: WPS204
            ),
        )

    def rd_tsconf(self) -> FieldValue:
        """Чтение текущего значения регистра конфигурации термодатчиков TSCONF.

        Returns:
            Текущее значение регистра конфигурации термодатчиков TSCONF

        """
        result = self._execute_command(
            cmd_fields=(CommandField(name=FieldName.CMD, value=FieldValue(SystemControl.RD_TSCONF), size=1),),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.DATA, size=1),
            ),
        )
        return next(field.value for field in result if field.name is FieldName.DATA)

    """ # noqa: WPS428, WPS462
    Команды для управления светодиодами панели АПУ-ЦВМ12Р
    """

    def wr_kpul(self, svk: Svk, data: FieldValue) -> None:
        """Запись новых состояний светодиодов КПУ ВК1 и ВК2.

        Args:
            svk: выбор ВК
            data: новые состояния светодиодов КПУ ВК1 и ВК2

        """
        self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(LedControl.WR_KPUL), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),  # noqa: WPS204
                CommandField(name=FieldName.DATA, value=data, size=1),
            ),
            result_fields=(  # noqa: WPS204
                ResultField(name=FieldName.RES, size=1),  # noqa: WPS204
                ResultField(name=FieldName.SVK, size=1),  # noqa: WPS204
                ResultField(name=FieldName.DATA, size=1),
            ),
        )

    def rd_kpul(self, svk: Svk) -> FieldValue:
        """Чтение текущих состояний светодиодов КПУ ВК1 и ВК2.

        Args:
            svk: выбор ВК

        Returns:
            Значение состояний светодиодов КПУ ВК1 и ВК2

        """
        result = self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(LedControl.RD_KPUL), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
                ResultField(name=FieldName.DATA, size=1),
            ),
        )
        return next(field.value for field in result if field.name is FieldName.DATA)

    def wr_kksl(self, svk: Svk, data: FieldValue) -> None:
        """Запись новых состояний светодиодов ККС ВК1 и ВК2.

        Args:
            svk: выбор ВК
            data: новые состояния светодиодов ККС ВК1 и ВК2

        """
        self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(LedControl.WR_KKSL), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
                CommandField(name=FieldName.DATA, value=data, size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
                ResultField(name=FieldName.DATA, size=1),
            ),
        )

    def rd_kksl(self, svk: Svk) -> FieldValue:
        """Чтение текущих состояний светодиодов ККС ВК1 и ВК2.

        Args:
            svk: выбор ВК

        Returns:
            Значение состояний светодиодов ККС ВК1 и ВК2

        """
        result = self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(LedControl.RD_KKSL), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
                ResultField(name=FieldName.DATA, size=1),
            ),
        )
        return next(field.value for field in result if field.name is FieldName.DATA)

    def wr_teleml(self, svk: Svk, data: FieldValue) -> None:
        """Запись новых состояний светодиодов телеметрии ВК1 и ВК2.

        Args:
            svk: выбор ВК
            data: новые состояния светодиодов телеметрии

        """
        self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(LedControl.WR_TELEML), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
                CommandField(name=FieldName.DATA, value=data, size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
                ResultField(name=FieldName.DATA, size=1),
            ),
        )

    def rd_teleml(self, svk: Svk) -> FieldValue:
        """Чтение текущих состояний светодиодов телеметрии ВК1 и ВК2.

        Args:
            svk: выбор ВК

        Returns:
            Текущее состояние светодиодов телеметрии.

        """
        result = self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(LedControl.RD_TELEML), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
                ResultField(name=FieldName.DATA, size=1),
            ),
        )
        return next(field.value for field in result if field.name is FieldName.DATA)

    def wr_prl(self, svk: Svk, data: FieldValue) -> None:
        """Запись новых состояний светодиодов прерывания ВК1 и ВК2.

        Args:
            svk: выбор ВК
            data: новые состояния светодиодов прерывания

        """
        self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(LedControl.WR_PRL), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
                CommandField(name=FieldName.DATA, value=data, size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
                ResultField(name=FieldName.DATA, size=1),
            ),
        )

    def rd_prl(self, svk: Svk) -> FieldValue:
        """Чтение текущих состояний светодиодов прерывания ВК1 и ВК2.

        Args:
            svk: выбор ВК

        Returns:
            Текущее состояние светодиодов прерывая ВК1 и ВК2

        """
        result = self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(LedControl.RD_PRL), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
                ResultField(name=FieldName.DATA, size=1),
            ),
        )
        return next(field.value for field in result if field.name is FieldName.DATA)

    """ # noqa: WPS428, WPS462
    Команды для управления кнопками АПУ-ЦВМ12Р
    """

    def get_kpub(self, svk: Svk) -> FieldValue:
        """Получение текущих состояний кнопок КПУ ВК1 и ВК2.

        Args:
            svk: выбор ВК

        Returns:
            Текущее состояние кнопок КПУ ВК1 и ВК2

        """
        result = self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(ButtonControl.GET_KPUB), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
                ResultField(name=FieldName.DATA, size=1),
            ),
        )
        return next(field.value for field in result if field.name is FieldName.DATA)

    def get_tkb(self, svk: Svk) -> FieldValue:
        """Получение текущих состояний кнопок смены ТК ВК1 и ВК2.

        Args:
            svk: выбор ВК

        Returns:
            Текущее состояние кнопок смены ТК ВК1 и ВК2

        """
        result = self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(ButtonControl.GET_TKB), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
                ResultField(name=FieldName.DATA, size=1),
            ),
        )
        return next(field.value for field in result if field.name is FieldName.DATA)

    def get_prb(self, svk: Svk) -> FieldValue:
        """Получение текущих состояний кнопок генерации прерывания ВК1 и ВК2.

        Args:
            svk: выбор ВК

        Returns:
            Текущее состояние кнопок генерации прерывания ВК1 и ВК2

        """
        result = self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(ButtonControl.GET_PRB), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
                ResultField(name=FieldName.DATA, size=1),
            ),
        )
        return next(field.value for field in result if field.name is FieldName.DATA)

    def track_kpub(self, svk: Svk, mode: CommandMode) -> None:
        """Включение/выключение отслеживания изменений состояний кнопок КПУ ВК1 и ВК2.

        Args:
            svk: выбор ВК
            mode: режим (включение/выключение)

        """
        cmd = ButtonControl.ON_TRACK_KPUB if mode else ButtonControl.OFF_TRACK_KPUB
        self._execute_command(
            cmd_fields=(  # noqa: WPS204
                CommandField(name=FieldName.CMD, value=FieldValue(cmd), size=1),  # noqa: WPS204
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
            ),
            result_fields=(  # noqa: WPS204
                ResultField(name=FieldName.RES, size=1),  # noqa: WPS204
                ResultField(name=FieldName.SVK, size=1),
            ),
        )

    def track_tkb(self, svk: Svk, mode: CommandMode) -> None:
        """Включение/выключение отслеживания изменений состояний кнопок смены ТК ВК1 и ВК2.

        Args:
            svk: выбор ВК
            mode: режим (включение/выключение)

        """
        cmd = ButtonControl.ON_TRACK_TKB if mode else ButtonControl.OFF_TRACK_TKB
        self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(cmd), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
            ),
        )

    def track_prb(self, svk: Svk, mode: CommandMode) -> None:
        """Включение/выключение отслеживания изменений состояний кнопок генерации прерывания ВК1 и ВК2.

        Args:
            svk: выбор ВК
            mode: режим (включение/выключение)

        """
        cmd = ButtonControl.ON_TRACK_PRB if mode else ButtonControl.OFF_TRACK_PRB
        self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(cmd), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
            ),
        )

    """ # noqa: WPS428, WPS462
    Команды для управления телеметрией АПУ-ЦВМ12Р
    """

    def get_kks(self, svk: Svk) -> FieldValue:
        """Получение текущих состояний сигналов ККС ВК1 и ВК2.

        Args:
            svk: выбор ВК

        Returns:
            Текущее состояние сигналов ККС ВК1 и ВК2.

        """
        result = self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(TelemetryControl.GET_KKS), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
                ResultField(name=FieldName.DATA, size=2),
            ),
        )
        return next(field.value.get_reversed_field() for field in result if field.name is FieldName.DATA)

    def get_pvp(self, svk: Svk) -> FieldValue:
        """Получение текущих состояний сигналов признаков вторичного питания ВК1 и ВК2.

        Args:
            svk: выбор ВК

        Returns:
            Текущее состояние сигналов признаков вторичного питания ВК1 и ВК2

        """
        result = self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(TelemetryControl.GET_PVP), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
                ResultField(name=FieldName.DATA, size=1),
            ),
        )
        return next(field.value for field in result if field.name is FieldName.DATA)

    def track_kks(self, svk: Svk, mode: CommandMode) -> None:
        """Включение/выключение отслеживания изменений состояний сигналов ККС ВК1 и ВК2.

        Args:
            svk: выбор ВК
            mode: режим (включение/выключение)

        """
        cmd = TelemetryControl.ON_TRACK_KKS if mode else TelemetryControl.OFF_TRACK_KKS
        self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(cmd), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
            ),
        )

    def track_pvp(self, svk: Svk, mode: CommandMode) -> None:
        """Включение/выключение отслеживания изменений сигналов признаков вторичного питания ВК1 и ВК2.

        Args:
            svk: выбор ВК
            mode: режим (включение/выключение)

        """
        cmd = TelemetryControl.ON_TRACK_PVP if mode else TelemetryControl.OFF_TRACK_PVP
        self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(cmd), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
            ),
        )

    """ # noqa: WPS428, WPS462
    Команды для управления КПУ и ТК АПУ-ЦВМ12Р1
    """

    def wr_kpu(self, svk: Svk, data: FieldValue) -> None:
        """Запись новых состояний сигналов КПУ ВК1 и ВК2.

        Args:
            svk: выбор ВК
            data: новые состояния сигналов КПУ ВК1 или ВК2

        """
        self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(KpuTkControl.WR_KPU), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
                CommandField(name=FieldName.DATA, value=data, size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
                ResultField(name=FieldName.DATA, size=1),
            ),
        )

    def rd_kpu(self, svk: Svk) -> FieldValue:
        """Чтение текущих состояний сигналов КПУ ВК1 и ВК2.

        Args:
            svk: выбор ВК

        Returns:
            Значение состояний сигналов КПУ ВК1 и ВК2

        """
        result = self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(KpuTkControl.RD_KPU), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
                ResultField(name=FieldName.DATA, size=1),
            ),
        )
        return next(field.value for field in result if field.name is FieldName.DATA)

    def track_kpu(self, svk: Svk, mode: CommandMode) -> None:
        """Включение/выключение отслеживания изменений состояний сигналов КПУ ВК1 и ВК2.

        Args:
            svk: выбор ВК
            mode: режим (включение/выключение)

        """
        cmd = KpuTkControl.ON_TRACK_KPU if mode else KpuTkControl.OFF_TRACK_KPU
        self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(cmd), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
            ),
        )

    def change_tk(self, svk: Svk, data: FieldValue) -> None:
        """Изменение состояний ТК ВК1 и ВК2.

        Args:
            svk: выбор ВК
            data: новые состояния ТК ВК1 или ВК2

        """
        self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(KpuTkControl.CHANGE_TK), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
                CommandField(name=FieldName.DATA, value=data, size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
                ResultField(name=FieldName.DATA, size=1),
            ),
        )

    def get_tk(self, svk: Svk) -> FieldValue:
        """Получение текущих состояний ТК ВК1 и ВК2.

        Args:
            svk: выбор ВК

        Returns:
            Текущие состояния ТК ВК1 или ВК2

        """
        result = self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(KpuTkControl.GET_TK), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
                ResultField(name=FieldName.DATA, size=1),
            ),
        )
        return next(field.value for field in result if field.name is FieldName.DATA)

    def track_tk(self, svk: Svk, mode: CommandMode) -> None:
        """Включение/выключение отслеживания изменения состояния ТК ВК1 и ВК2.

        Args:
            svk: выбор ВК
            mode: режим (включение/выключение)

        """
        cmd = KpuTkControl.ON_TRACK_TK if mode else KpuTkControl.OFF_TRACK_TK
        self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(cmd), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
            ),
        )

    """ # noqa: WPS428, WPS462
    Команды для управления КС АПУ-ЦВМ12Р
    """

    def wr_gp_param(self, svk: Svk, param_type: TypeGpParam, data: FieldValue) -> None:
        """Запись нового значения параметра генерации сигнала КС ВК1 и ВК2.

        Args:
            svk: выбор ВК
            param_type: тип записываемого параметра ВК1 или ВК2
            data: новое значение записываемого параметра генератора импульса

        """
        self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(KsControl.WR_GP_PARAM), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
                CommandField(name=FieldName.TYPE, value=FieldValue(param_type), size=1),  # noqa: WPS204
                CommandField(name=FieldName.DATA, value=data, size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
                ResultField(name=FieldName.TYPE, size=1),  # noqa: WPS204
                ResultField(name=FieldName.DATA, size=1),
            ),
        )

    def rd_gp_param(self, svk: Svk, param_type: TypeGpParam) -> FieldValue:
        """Чтение текущего значения параметра генерации сигнала КС ВК1 и ВК2.

        Args:
            svk: выбор ВК
            param_type: тип записываемого параметра ВК1 или ВК2

        Returns:
            Значение параметра генерации сигнала КС

        """
        result = self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(KsControl.RD_GP_PARAM), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
                CommandField(name=FieldName.TYPE, value=FieldValue(param_type), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
                ResultField(name=FieldName.TYPE, size=1),
                ResultField(name=FieldName.DATA, size=1),
            ),
        )
        return next(field.value for field in result if field.name is FieldName.DATA)

    def wr_gp_mode(self, svk: Svk, data: FieldValue) -> None:
        """Запись нового значения режимов работы генераторов импульсов ВК1 и ВК2.

        Args:
            svk: выбор ВК
            data: новое значение режимов генераторов импульсов

        """
        self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(KsControl.WR_GP_MODE), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
                CommandField(name=FieldName.DATA, value=data, size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
                ResultField(name=FieldName.DATA, size=1),
            ),
        )

    def rd_gp_mode(self, svk: Svk) -> FieldValue:
        """Чтение текущего значения режимов работы генераторов импульсов ВК1 и ВК2.

        Args:
            svk: выбор ВК

        Returns:
            Значение режимов работы генераторов импульсов

        """
        result = self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(KsControl.RD_GP_MODE), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
                ResultField(name=FieldName.DATA, size=1),
            ),
        )
        return next(field.value for field in result if field.name is FieldName.DATA)

    def wr_gp_etrans(self, svk: Svk, data: FieldValue) -> None:
        """Запись нового значения в регистр включения генераторов импульсов ВК1 и ВК2.

        Args:
            svk: выбор ВК
            data: новое значение для записи

        """
        self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(KsControl.WR_GP_ETRANS), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
                CommandField(name=FieldName.DATA, value=data, size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
                ResultField(name=FieldName.DATA, size=1),
            ),
        )

    def rd_gp_etrans(self, svk: Svk) -> FieldValue:
        """Чтение текущего значения регистра включения генераторов импульсов ВК1 и ВК2.

        Args:
            svk: выбор ВК

        Returns:
            Значение регистра включения генераторов импульсов

        """
        result = self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(KsControl.RD_GP_ETRANS), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
                ResultField(name=FieldName.DATA, size=1),
            ),
        )
        return next(field.value for field in result if field.name is FieldName.DATA)

    def run_gp(self, svk: Svk, data: FieldValue) -> None:
        """Запуск генераторов импульсов ВК1 и ВК2.

        Args:
            svk: выбор ВК
            data: новое значение регистра запуска генераторов импульсов

        """
        self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(KsControl.RUN_GP), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
                CommandField(name=FieldName.DATA, value=data, size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
                ResultField(name=FieldName.DATA, size=1),
            ),
        )

    def get_gp_prd(self, svk: Svk) -> FieldValue:
        """Получение последних сохранённых значений флагов завершения очередного импульса ВК1 и ВК2.

        Args:
            svk: выбор ВК

        Returns:
            Последние сохраненные состояния флагов завершения очередных импульсов генераторов импульсов

        """
        result = self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(KsControl.GET_GP_PRD), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
                ResultField(name=FieldName.DATA, size=1),
            ),
        )
        return next(field.value for field in result if field.name is FieldName.DATA)

    def get_gp_stp(self, svk: Svk) -> FieldValue:
        """Получение значений флагов остановленных генераторов импульсов ВК1 и ВК2.

        Args:
            svk: выбор ВК

        Returns:
            Текущие состояния флагов остановленных генераторов импульсов

        """
        result = self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(KsControl.GET_GP_STP), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
                ResultField(name=FieldName.DATA, size=1),
            ),
        )
        return next(field.value for field in result if field.name is FieldName.DATA)

    def get_gp_prd_ct(self, svk: Svk, param_type: TypeGetGpPrdCt) -> FieldValue:
        """Получение значения количества пройденных периодов генерации импульса генераторов импульсов ВК1 и ВК2.

        Args:
            svk: выбор ВК
            param_type: выбор текущего значения количества пройденных периодов генерации импульсов
                               генераторов импульсов

        Returns:
            Текущее значение количества пройденных периодов генерации импульса генератора импульса

        """
        result = self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(KsControl.GET_GP_PRD_CT), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
                CommandField(name=FieldName.TYPE, value=FieldValue(param_type), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
                ResultField(name=FieldName.TYPE, size=1),
                ResultField(name=FieldName.DATA, size=2),
            ),
        )
        return next(field.value.get_reversed_field() for field in result if field.name is FieldName.DATA)

    def track_gp_prd(self, svk: Svk, mode: CommandMode) -> None:
        """Включить/выключить отслеживание значений флагов завершения очередного импульса ВК1 и ВК2.

        Args:
            svk: выбор ВК
            mode: режим (включение/выключение)

        """
        cmd = KsControl.ON_TRACK_GP_PRD if mode else KsControl.OFF_TRACK_GP_PRD
        self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(cmd), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
            ),
        )

    def track_gp_stp(self, svk: Svk, mode: CommandMode) -> None:
        """Включить/выключить отслеживание значений флагов остановленных генераторов импульсов ВК1 и ВК2.

        Args:
            svk: выбор ВК
            mode: режим (включение/выключение)

        """
        cmd = KsControl.ON_TRACK_GP_STP if mode else KsControl.OFF_TRACK_GP_STP
        self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(cmd), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
            ),
        )

    """ # noqa: WPS428, WPS462
    Команды для управления ЭНПЗУ АПУ-ЦВМ12Р
    """

    def wr_eeprom(self, addr: FieldValue, data: FieldValue) -> None:
        """Запись данных в ЭНПЗУ.

        Args:
            addr: адрес, по которому происходит запись данных в ЭНПЗУ
            data: записываемые данные в ЭНПЗУ

        """
        self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(EnpzuControl.WR_EEPROM), size=1),
                CommandField(name=FieldName.ADDR, value=addr.get_reversed_field(), size=2),
                CommandField(name=FieldName.DATA, value=data, size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.ADDR, size=2),
                ResultField(name=FieldName.DATA, size=1),
            ),
        )

    def rd_eeprom(self, addr: FieldValue) -> FieldValue:
        """Чтение данных из ЭНПЗУ.

        Args:
            addr: адрес, по которому происходит чтение данных из ЭНПЗУ

        Returns:
            Считанные данные из ЭНПЗУ

        """
        result = self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(EnpzuControl.RD_EEPROM), size=1),
                CommandField(name=FieldName.ADDR, value=addr.get_reversed_field(), size=2),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.ADDR, size=2),
                ResultField(name=FieldName.DATA, size=1),
            ),
        )
        return next(field.value.get_reversed_field() for field in result if field.name is FieldName.DATA)

    def rd_sts_eeprom(self) -> FieldValue:
        """Чтение статусного регистра ЭНПЗУ.

        Returns:
            Считанное значение регистра статуса ЭНПЗУ

        """
        result = self._execute_command(
            cmd_fields=(CommandField(name=FieldName.CMD, value=FieldValue(EnpzuControl.RD_STS_EEPROM), size=1),),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.DATA, size=1),
            ),
        )
        return next(field.value for field in result if field.name is FieldName.DATA)

    """ # noqa: WPS428, WPS462
    Команды для управления контроллерами 1 Wire АПУ-ЦВМ12Р
    """

    def wr_ow_reg(self, svk: Svk, param_type: TypeWrOwReg, data: FieldValue) -> None:
        """Запись нового значения в управляющий регистр контроллеров 1 Wire ВК1 и ВК2.

        Args:
            svk: выбор ВК
            param_type: выбор управляющего регистра контроллера 1 Wire
            data: новое значение регистра

        """
        self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(OneWireControl.WR_OW_REG), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
                CommandField(name=FieldName.TYPE, value=FieldValue(param_type), size=1),
                CommandField(name=FieldName.DATA, value=data, size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
                ResultField(name=FieldName.TYPE, size=1),
                ResultField(name=FieldName.DATA, size=1),
            ),
        )

    def rd_ow_reg(self, svk: Svk, param_type: TypeRdOwReg) -> FieldValue:
        """Чтение текущего значения управляющего регистра контроллеров 1 Wire ВК1 и ВК2.

        Args:
            svk: выбор ВК
            param_type: выбор управляющего регистра контроллера 1 Wire

        Returns:
            Текущее значение регистра

        """
        result = self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(OneWireControl.RD_OW_REG), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
                CommandField(name=FieldName.TYPE, value=FieldValue(param_type), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
                ResultField(name=FieldName.TYPE, size=1),
                ResultField(name=FieldName.DATA, size=1),
            ),
        )
        return next(field.value for field in result if field.name is FieldName.DATA)

    """ # noqa: WPS428, WPS462
    Команды для управления контроллерами UART АПУ-ЦВМ12Р
    """

    def wr_uart_reg(self, param_type: TypeWrUartReg, data: FieldValue) -> None:
        """Запись нового значения в управляющий регистр контроллера UART 0.

        Args:
            param_type: выбор управляющего регистра контроллера UART 0
            data: новое значение регистра

        """
        self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(UartControl.WR_UART_REG), size=1),
                CommandField(name=FieldName.TYPE, value=FieldValue(param_type), size=1),
                CommandField(name=FieldName.DATA, value=data, size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.TYPE, size=1),
                ResultField(name=FieldName.DATA, size=1),
            ),
        )

    def rd_uart_reg(self, param_type: TypeRdUartReg) -> FieldValue:
        """Чтение текущего значения управляющего регистра контроллера UART 0.

        Args:
            param_type: выбор управляющего регистра контроллера UART 0

        Returns:
            Текущее значение регистра

        """
        result = self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(UartControl.RD_UART_REG), size=1),
                CommandField(name=FieldName.TYPE, value=FieldValue(param_type), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.TYPE, size=1),
                ResultField(name=FieldName.DATA, size=1),
            ),
        )
        return next(field.value for field in result if field.name is FieldName.DATA)

    """ # noqa: WPS428, WPS462
    Команды для управления матричном коммутатором АПУ-ЦВМ12Р
    """

    def connect_rx_tx(self, rxd: TypeMatrixRXD, txd: TypeMatrixTXD) -> None:
        """Подключение линии приема данных RXD к линии передачи данных TXD.

        Args:
            rxd: идентификатор подключаемой линии передачи данных RXD
            txd: идентификатор линии передачи данных TXD

        """
        self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(MatrixControl.CONNECT_RX_TX), size=1),
                CommandField(name=FieldName.RXD, value=FieldValue(rxd), size=1),
                CommandField(name=FieldName.TXD, value=FieldValue(txd), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.RXD, size=1),
                ResultField(name=FieldName.TXD, size=1),
            ),
        )

    def disconnect_tx(self, txd: TypeMatrixTXD) -> None:
        """Отключение линии передачи данных TXD.

        Args:
            txd: идентификатор линии передачи данных TXD

        """
        self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(MatrixControl.DISCONNECT_TX), size=1),
                CommandField(name=FieldName.TYPE, value=FieldValue(txd), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.TXD, size=1),
            ),
        )

    def wr_defval(self, data: FieldValue) -> None:
        """Запись новых значений по умолчанию линий передачи данных TXD.

        Args:
            data: новые значения по умолчанию линий передачи данных TXD

        """
        self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(MatrixControl.WR_DEFVAL), size=1),
                CommandField(name=FieldName.TYPE, value=data, size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.DATA, size=1),
            ),
        )

    def rd_defval(self) -> FieldValue:
        """Чтение текущих значений по умолчанию линий передачи данных TXD.

        Returns:
            Текущие значения по умолчанию линий передачи данных TXD

        """
        result = self._execute_command(
            cmd_fields=(CommandField(name=FieldName.CMD, value=FieldValue(MatrixControl.RD_DEFVAL), size=1),),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.DATA, size=1),
            ),
        )
        return next(field.value for field in result if field.name is FieldName.DATA)

    def get_rx(self, txd: TypeMatrixTXD) -> FieldValue:
        """Получение текущей линии приема данных RXD у линии передачи данных TXD.

        Args:
            txd: идентификатор линии передачи данных TXD

        Returns:
            Идентификатор подключенной линии передачи данных RXD

        """
        result = self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(MatrixControl.GET_RX), size=1),
                CommandField(name=FieldName.TXD, value=FieldValue(txd), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.TXD, size=1),
                ResultField(name=FieldName.RXD, size=1),
            ),
        )
        return next(field.value for field in result if field.name is FieldName.RXD)

    """ # noqa: WPS428, WPS462
    Команды для управления термодатчиками АПУ-ЦВМ12Р
    """

    def search_ts(self, svk: Svk) -> FieldValue:
        """Поиск идентификаторов термодатчиков ВК1 и ВК2.

        Args:
            svk: выбор ВК

        Returns:
            Результаты поиска термодатчиков

        """
        result = self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(ThermalSensorControl.SEARCH_TS), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
                ResultField(name=FieldName.DATA, size=1),
            ),
        )
        return next(field.value for field in result if field.name is FieldName.DATA)

    def get_ids_ts(self, svk: Svk) -> tuple[FieldValue, ...]:
        """Получение идентификаторов термодатчиков ВК1 и ВК2.

        Args:
            svk: выбор ВК

        Returns:
            Идентификаторы найденных термодатчиков

        """
        cmd_fields = (
            CommandField(name=FieldName.CMD, value=FieldValue(ThermalSensorControl.GET_IDS_TS), size=1),
            CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
        )
        _validate_args(cmd_fields=cmd_fields)
        self._send_command(cmd_fields)
        read_res = _bytes_to_int(self._read(1))
        if read_res != ThermalSensorControl.GET_IDS_TS:
            _raise_serial_result_error(
                command=ThermalSensorControl.GET_IDS_TS,
                name=FieldName.RES.value,
                expected=ThermalSensorControl.GET_IDS_TS,
                received=read_res,
            )
        read_svk = _bytes_to_int(self._read(1))
        if read_svk != svk:
            _raise_serial_result_error(
                command=ThermalSensorControl.GET_IDS_TS,
                name=FieldName.SVK.value,
                expected=svk,
                received=read_svk,
            )
        read_count = _bytes_to_int(self._read(1))
        return tuple(FieldValue(self._read(8)).get_reversed_field() for _ in range(read_count))

    def measure_temp(self, svk: Svk, param_type: TypeTemp) -> None:
        """Запуск измерения температуры термодатчиками ВК1 и ВК2.

        Args:
            svk: выбор ВК
            param_type: выбор адресного диапазона хранения данных температуры

        """
        self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(ThermalSensorControl.MEASURE_TEMP), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
                CommandField(name=FieldName.TYPE, value=FieldValue(param_type), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
                ResultField(name=FieldName.TYPE, size=1),
            ),
        )

    def get_temp(self, svk: Svk, param_type: TypeTemp) -> tuple[FieldValue, ...]:
        """Получение измеренной температуры термодатчиками ВК1 и ВК2.

        Args:
            svk: выбор ВК
            param_type: выбор адресного диапазона хранения данных температуры

        Returns:
            Значения температур, измеренных датчиками

        """
        cmd_fields = (
            CommandField(name=FieldName.CMD, value=FieldValue(ThermalSensorControl.GET_TEMP), size=1),
            CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
            CommandField(name=FieldName.TYPE, value=FieldValue(param_type), size=1),
        )
        _validate_args(cmd_fields=cmd_fields)
        self._send_command(cmd_fields)
        read_res = _bytes_to_int(self._read(1))
        if read_res != ThermalSensorControl.GET_TEMP:
            _raise_serial_result_error(
                command=ThermalSensorControl.GET_TEMP,
                name=FieldName.RES.value,
                expected=ThermalSensorControl.GET_TEMP,
                received=read_res,
            )
        read_svk = _bytes_to_int(self._read(1))
        if read_svk != svk:
            _raise_serial_result_error(
                command=ThermalSensorControl.GET_TEMP,
                name=FieldName.SVK.value,
                expected=svk,
                received=read_svk,
            )
        read_type = _bytes_to_int(self._read(1))
        if read_type != param_type:
            _raise_serial_result_error(
                command=ThermalSensorControl.GET_TEMP,
                name=FieldName.TYPE.value,
                expected=param_type,
                received=read_type,
            )
        read_count = _bytes_to_int(self._read(1))
        return tuple(FieldValue(self._read(2)).get_reversed_field() for _ in range(read_count))

    def measure_temp_id(self, svk: Svk, param_type: TypeTemp, param_id: FieldValue) -> bool:
        """Запуск измерения температуры определенным термодатчиком ВК1 и ВК2.

        Args:
            svk: выбор ВК
            param_type: выбор адресного диапазона хранения данных температуры
            param_id: идентификатор термодатчика

        Returns:
            True - термодатчик найден и измерение температуры запущено, False - термодатчик не найден

        """
        result = self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(ThermalSensorControl.MEASURE_TEMP_ID), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
                CommandField(name=FieldName.TYPE, value=FieldValue(param_type), size=1),
                CommandField(name=FieldName.ID, value=param_id.get_reversed_field(), size=8),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
                ResultField(name=FieldName.TYPE, size=1),
                ResultField(name=FieldName.FIND, size=1),
                ResultField(name=FieldName.ID, size=8),
            ),
        )
        return next(field.value.get_int_value() for field in result if field.name is FieldName.FIND) != 0

    def get_temp_id(self, svk: Svk, param_type: TypeTemp, param_id: FieldValue) -> FieldValue:
        """Получение измеренной температуры определенного термодатчика ВК1 и ВК2.

        Args:
            svk: выбор ВК
            param_type: выбор адресного диапазона хранения данных температуры
            param_id: идентификатор термодатчика

        Returns:
            Значение температуры измеренного термодатчиком,
                если термодатчик не найден значение температуры равно 0x0000

        """
        result = self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(ThermalSensorControl.GET_TEMP_ID), size=1),
                CommandField(name=FieldName.SVK, value=FieldValue(svk), size=1),
                CommandField(name=FieldName.TYPE, value=FieldValue(param_type), size=1),
                CommandField(name=FieldName.ID, value=param_id.get_reversed_field(), size=8),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.SVK, size=1),
                ResultField(name=FieldName.TYPE, size=1),
                ResultField(name=FieldName.FIND, size=1),
                ResultField(name=FieldName.ID, size=8),
                ResultField(name=FieldName.T, size=2),
            ),
        )
        return next(field.value for field in result if field.name is FieldName.T)

    """ # noqa: WPS428, WPS462
    Команды для управления таймерами АПУ-ЦВМ12Р
    """

    def wr_wcnt(self, param_type: TypeTmr, data: FieldValue) -> None:
        """Запись нового значения в регистр WCNT.

        Args:
            param_type: выбор таймера
            data: новое значение регистра

        """
        self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(TimerControl.WR_WCNT), size=1),
                CommandField(name=FieldName.TYPE, value=FieldValue(param_type), size=1),
                CommandField(name=FieldName.DATA, value=data.get_reversed_field(), size=2),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.TYPE, size=1),
                ResultField(name=FieldName.DATA, size=2),
            ),
        )

    def rd_wcnt(self, param_type: TypeTmr) -> FieldValue:
        """Чтение текущего значения регистра WCNT.

        Args:
            param_type: выбор таймера

        Returns:
            Текущее значение регистра

        """
        result = self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(TimerControl.RD_WCNT), size=1),
                CommandField(name=FieldName.TYPE, value=FieldValue(param_type), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.TYPE, size=1),
                ResultField(name=FieldName.DATA, size=2),
            ),
        )
        return next(field.value.get_reversed_field() for field in result if field.name is FieldName.DATA)

    def rd_rcnt(self, param_type: TypeTmr) -> FieldValue:
        """Чтение текущего значения регистра RCNT.

        Args:
            param_type: выбор таймера

        Returns:
            Значение регистра

        """
        result = self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(TimerControl.RD_RCNT), size=1),
                CommandField(name=FieldName.TYPE, value=FieldValue(param_type), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.TYPE, size=1),
                ResultField(name=FieldName.DATA, size=2),
            ),
        )
        return next(field.value.get_reversed_field() for field in result if field.name is FieldName.DATA)

    def run_tmr(self, param_type: TypeTmr) -> None:
        """Запуск таймера.

        Args:
            param_type: выбор таймера

        """
        self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(TimerControl.RUN_TMR), size=1),
                CommandField(name=FieldName.TYPE, value=FieldValue(param_type), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.TYPE, size=1),
            ),
        )

    def rst_tmr(self, param_type: TypeTmr) -> None:
        """Сброс таймера.

        Args:
            param_type: выбор таймера

        """
        self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(TimerControl.RST_TMR), size=1),
                CommandField(name=FieldName.TYPE, value=FieldValue(param_type), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.TYPE, size=1),
            ),
        )

    def check_tmr(self, param_type: TypeTmr) -> FieldValue:
        """Проверка таймера.

        Args:
            param_type: выбор таймера

        Returns:
            Количество срабатываний выбранного таймера

        """
        result = self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(TimerControl.CHECK_TMR), size=1),
                CommandField(name=FieldName.TYPE, value=FieldValue(param_type), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.TYPE, size=1),
                ResultField(name=FieldName.DATA, size=2),
            ),
        )
        return next(field.value.get_reversed_field() for field in result if field.name is FieldName.DATA)

    def track_tmr(self, param_type: TypeTmr, mode: CommandMode) -> None:
        """Включить/выключить отслеживание таймера.

        Args:
            param_type: выбор таймера
            mode: режим (включение/выключение)

        """
        cmd = TimerControl.ON_TRACK_TMR if mode else TimerControl.OFF_TRACK_TMR
        self._execute_command(
            cmd_fields=(
                CommandField(name=FieldName.CMD, value=FieldValue(cmd), size=1),
                CommandField(name=FieldName.TYPE, value=FieldValue(param_type), size=1),
            ),
            result_fields=(
                ResultField(name=FieldName.RES, size=1),
                ResultField(name=FieldName.TYPE, size=1),
            ),
        )

    def _execute_command(
        self,
        cmd_fields: tuple[CommandField, ...],
        result_fields: tuple[ResultField, ...],
    ) -> tuple[ReadResultField, ...] | None:
        """Исполнение команды.

        Args:
            cmd_fields: Поля команды (аргументы)
            result_fields: Поля, которые нужно считать. В формате имя поля, кол-во считываемых байт.

        Returns:
            Результаты выполнения команды или None.

        """
        _validate_args(cmd_fields)
        self._send_command(cmd_fields)
        read_result = self._read_all_results(result_fields)
        return _validate_and_collect_results(cmd_fields, read_result)

    def _send_command(self, cmd_fields: tuple[CommandField, ...]) -> None:
        """Отправляет команду на устройство.

        Args:
            cmd_fields: аргументы (поля) команды

        """
        for field in cmd_fields:
            if field.name == FieldName.CMD and field.value.get_int_value() == SystemControl.CONNECT:
                for _ in range(CONNECT_COUNT):
                    self._connection.write(field.value.bytes_value)
            else:
                self._connection.write(field.value.bytes_value)

    def _read_all_results(self, result_fields: tuple[ResultField, ...]) -> tuple[ReadResultField, ...]:
        """Считывает результаты выполнения команды.

        Args:
            result_fields: поля результата команды

        Returns:
            Считанный результат работы команды

        """
        return tuple(
            ReadResultField(name=field.name, value=FieldValue(self._read(field.size))) for field in result_fields
        )

    def _read(self, size: int) -> bytes:
        """Считывание байт из COM-порта.

        Args:
            size: кол-во байт на считывание.

        Returns:
            Считанный результат

        Raises:
            SerialResultError: Если от устройства не поступило ожидаемое кол-во байт

        """
        result = self._connection.read(size=size)
        len_result = len(result)
        if len_result == size:
            return result
        msg = f'ОШИБКА! Ожидалось {size} байт, получено {len_result}'
        raise SerialResultError(msg)


def _raise_serial_result_error(command: int, name: str, expected: int, received: int):
    raise SerialResultError(
        'ОШИБКА в результате выполнения команды '
        + hex(command)
        + ': '
        + COMMAND_DESCRIPTION[command]
        + '\nОжидаемое значение поля '
        + name
        + ': '
        + hex(expected)
        + ', получено: '
        + hex(received)
        + '\n',
    )


def _handle_invalid_result(
    cmd_fields: tuple[CommandField, ...],
    read_name: FieldName,
    read_value: FieldValue,
) -> None:
    """Обрабатывает некорректный результат, вызывая исключение.

    Args:
        cmd_fields: поля команды (аргументы)
        read_name: имя считанного поля результата
        read_value: считанное значение

    """
    command = next(field.value.get_int_value() for field in cmd_fields if field.name is FieldName.CMD)
    if read_name is FieldName.RES:
        expected = command
    else:
        expected = next(field.value.get_int_value() for field in cmd_fields if field.name is read_name)
    _raise_serial_result_error(
        command=command,
        name=read_name.value,
        expected=expected,
        received=read_value.get_int_value(),
    )


def _is_valid_result(  # noqa: PLR0911
    cmd_fields: tuple[CommandField, ...],
    read_name: FieldName,
    read_value: FieldValue,
    results_to_return: list[ReadResultField],
) -> bool:
    """Проверяет, является ли результат валидным.

    Args:
        cmd_fields: поля команды (аргументы)
        read_name: имя считанного поля результата
        read_value: считанное значение
        results_to_return: полученный результат

    Returns:
        True - если валидный результат

    """
    if read_name == FieldName.RES:
        cmd_value = tuple(field.value.bytes_value for field in cmd_fields if field.name is FieldName.CMD)
        if cmd_value:
            return cmd_value[0] == read_value.bytes_value
        return False
    if read_name == FieldName.ID:
        find_value = tuple(field.value.get_int_value() for field in results_to_return if field.name is FieldName.FIND)
        if find_value:
            if find_value[0] == 0:
                return read_value.get_int_value() == 0
            return read_value.get_int_value() != 0
        return False
    repeated_value = tuple(field for field in cmd_fields if field.name is read_name)
    if repeated_value:
        return repeated_value[0].value.bytes_value == read_value.bytes_value
    return True


def _validate_and_collect_results(
    cmd_fields: tuple[CommandField, ...],
    read_fields: tuple[ReadResultField, ...],
) -> tuple[ReadResultField, ...] | None:
    """Проверяет результаты и собирает валидные.

    Args:
        cmd_fields: поля команды (аргументы)
        read_fields: считанный результат

    Returns:
        Возвращаемый результат выполнения команды

    """
    results_to_return: list[ReadResultField] = []
    fields_names = tuple(field.name for field in cmd_fields)
    for read_field in read_fields:
        if not _is_valid_result(cmd_fields, read_field.name, read_field.value, results_to_return):
            _handle_invalid_result(cmd_fields, read_field.name, read_field.value)
        # Возвращаем только те поля результата, которых не было в полях команды
        if read_field.name not in fields_names and read_field.name != FieldName.RES:
            results_to_return.append(ReadResultField(name=read_field.name, value=read_field.value))

    return tuple(results_to_return) if results_to_return else None


def _validate_args(cmd_fields: tuple[CommandField, ...]) -> None:
    """Проверяет размер переданных аргументов.

    Args:
        cmd_fields: поля команды (аргументы)

    Raises:
        ArgumentSizeError: если передан аргумент неверного размера

    """
    for cmd_field in cmd_fields:
        passed_size = len(cmd_field.value.bytes_value)
        expected_size = cmd_field.size
        if passed_size != expected_size:
            command = 0
            for field in cmd_fields:
                if field.name is FieldName.CMD:
                    command = field.value.get_int_value()
                    break
            raise ArgumentSizeError(
                'Ошибка в команде '
                + hex(command)
                + COMMAND_DESCRIPTION[command]
                + '\nОжидаемый размер аргумента '
                + str(cmd_field.name.value)
                + ': '
                + str(expected_size)
                + ' байт, передано: '
                + str(passed_size)
                + ' байт\n',
            )
