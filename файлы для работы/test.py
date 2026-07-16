import time

import set_apupp
from apupp import Apupp, FieldValue, Svk

PAUSE_SECONDS = 2

# значения КПУ
KPU_VALUES = [
    [0, 0, 0, 0],
    [1, 0, 0, 0],
    [0, 1, 0, 0],
    [1, 1, 1, 1],
    [0, 0, 0, 0],
]

def run() -> None:
    set_apupp.run()  # переключение пульта в режим АПУПП

    with Apupp() as apu:
        for value in KPU_VALUES:
            apu.wr_kpu(svk=Svk.VK1, data=FieldValue(value))
            print(f'КПУ ВК1 установлен в {value}')
            time.sleep(PAUSE_SECONDS)

            read_back = apu.rd_kpu(svk=Svk.VK1).get_list_value()
            status = 'OK' if read_back == value else 'MISMATCH'
            print(f'Считано КПУ ВК1: {read_back} [{status}]')

if __name__ == '__main__':
    run()