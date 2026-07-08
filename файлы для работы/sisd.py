"""Модуль для работы с АПУ-ЦВМ12Р через протокол SISD."""

import serial
from config import PORT, BAUDRATE

CONNECT_COUNT = 32

EMPTY_BYTE = 0x0
SPBT_WR = 0x18
SPBT_RD = 0x58
SPBR_WR = 0x1B
SPBR_RD = 0x5B
FID = 0x0
A3 = 0x0
MAX_BYTE_VALUE = 255

RD_ADDR_LEN = 2
WR_ADDR_LEN = 2


def _get_be(addr_in_block: int) -> int:
    str_value = ''.join(['0' if idx == addr_in_block else '1' for idx in range(8)])
    return int(str_value[::-1], 2)


class Sisd:  # noqa: WPS214
    """Модуль для работы с АПУ-ЦВМ12Р через протокол SISD."""

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
        self._connect_apu()

    def __del__(self):  # noqa: WPS603
        """Деструктор класса."""
        self._disconnect_apu()
        self._connection.close()

    def change_to_apupp(self):
        """Переводит АПУ в режим работы по протоколу АПУПП.

        Returns:
            bool: успешное или неуспешное выполнение команды

        """
        return self._exec_wr(addr=bytes([0x50, 0x4]), value=0x6)

    def set_mask_kpu(self, value: int) -> None:  # noqa: WPS615
        """Устанавливает маску обработки (процессором) прерываний от нажатия кнопок КПУ.

        Args:
            value: значение записываемой маски

        """
        self._exec_wr(addr=bytes([0x46, 0x81]), value=value)

    def get_kpub(self) -> int:  # noqa: WPS615
        """Считывает значение регистра кнопок КПУ.

        Returns:
            Состояние кнопок КПУ.

        """
        return self._exec_rd(addr=bytes([0x10, 0x1]))

    def get_mask_kpu(self) -> int:  # noqa: WPS615
        """Считывает значение регистра маски обработки прерываний от нажатия кнопок КПУ.

        Returns:
            Значение маски КПУ

        """
        return self._exec_rd(addr=bytes([0x46, 0x81]))

    def _exec_wr(self, addr: bytes, value: int) -> None:
        if len(addr) != WR_ADDR_LEN:
            msg = 'Длина адреса команды WR должна быть 2 байта.'
            raise ValueError(msg)
        if value > MAX_BYTE_VALUE or value < 0:
            msg = 'Нельзя записать в регистр значение больше чем 1 байт.'
            raise ValueError(msg)
        addr_in_block = addr[-1] & 0x7
        cmd_code = bytes([SPBT_WR, FID, addr[1], addr[0], A3, _get_be(addr_in_block=addr_in_block)])
        cmd_code += bytes([value if idx == addr_in_block else EMPTY_BYTE for idx in range(8)])
        self._connection.write(cmd_code)
        result = self._connection.read(10)
        check_spbr = result[0] == SPBR_WR
        check_fid = result[1] == FID
        check_wr_data = result[2 + addr_in_block] == value
        if not (check_spbr and check_fid and check_wr_data):
            raise ValueError

    def _exec_rd(self, addr: bytes) -> int:
        if len(addr) != RD_ADDR_LEN:
            msg = 'Длина адреса команды RD должна быть 2 байта.'
            raise ValueError(msg)
        addr_in_block = addr[-1] & 0x7
        cmd_code = bytes([SPBT_RD, FID, addr[1], addr[0], A3, _get_be(addr_in_block=addr_in_block)])
        self._connection.write(cmd_code)
        result = self._connection.read(10)
        check_spbr = result[0] == SPBR_RD
        check_fid = result[1] == FID
        if not (check_spbr and check_fid):
            raise ValueError
        return result[2 + addr_in_block]

    def _connect_apu(self) -> bool:
        """Подключение к АПУ.

        Returns:
            bool: Успешное подключение

        """
        self._connection.write(bytes([0 for _ in range(CONNECT_COUNT)]))
        return self._connection.read(2) == bytes([0x0, 0x1A])

    def _disconnect_apu(self) -> bool:
        """Отключение от АПУ.

        Returns:
            bool: Успешное отключение

        """
        self._connection.write(bytes([0x4]))
        return self._connection.read(1) == bytes([0x4])
