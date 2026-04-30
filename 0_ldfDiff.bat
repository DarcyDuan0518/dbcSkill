  
@echo off
chcp 65001 >nul
python ldf_batch_diff.py ^
    "data/PZBP3.1.8通信矩阵_CAN_V10.1.7_SOA_V10.1.10_0409" ^
    "data/PZBP3.4.0通信矩阵_CAN_V11.1.0_SOA_V11.1.1_0421" ^
    -o ldf_diff_output
pause