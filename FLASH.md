# X99-CH8 改版 BIOS 刷入說明

## 檔案

| 檔案 | 用途 |
|---|---|
| `X99-CH8_G3X99018_rebar_only.bin` | 只加 ReBarDxe，沒有 GOP。風險最低，建議第一次刷這個 |
| `X99-CH8_G3X99018_rebar_astgop.bin` | 加了 ReBarDxe 和 AST2400 GOP。晶片已用 lspci 確認是 AST2400（rev 30），可以刷 |
| `*.sha256` | 對應映像的 sha256 |
| `dump1.bin` | 你板子的原始備份，救磚用 |
| `X99-CH8v3.022-08-27.zip` 裡的 `99CH8.bin` | 官方原廠映像，也可救磚，但不含你的設定 |

三個都是完整 16 MiB SPI 映像，含 descriptor、ME、BIOS region，CH341A 可直接整顆寫入。

## 刷之前

1. 核對 hash：

   ```bash
   sha256sum -c X99-CH8_G3X99018_rebar_only.bin.sha256
   sha256sum -c X99-CH8_G3X99018_rebar_astgop.bin.sha256
   ```

2. 確認 `dump1.bin` 另外存一份在別台機器或隨身碟。
3. 把 BIOS 晶片型號看清楚，應該是 Winbond W25Q128，3.3V。
4. AST 晶片已於 2026-10-27 用 `lspci` 確認：`08:00.0 ASPEED Graphics Family (rev 30)`，前面掛 AST1150 橋，是 AST2400。含 GOP 的映像可以直接刷。
5. 同一份 lspci 也顯示 Above 4G Decoding 目前已開啟，裝置 BAR 都在 56T 的 MMIO High 視窗。
6. 想更保守的話，可先刷 `rebar_only` 確認流程，再刷 `rebar_astgop`。兩者差別只是多一個 GOP 檔案。

## 用 CH341A 刷

1. 主機完全斷電，拔掉電源線，按一下電源鍵放電。
2. 夾子夾上 BIOS 晶片，紅線對第 1 腳的圓點。如果晶片是 DIP-8 插座，直接拔下來插到燒錄器上更穩。
3. 先讀一次，確認讀得到，而且和 `dump1.bin` 一樣：

   ```bash
   flashrom -p ch341a_spi -r check.bin
   cmp check.bin dump1.bin && echo SAME
   ```

   讀不到或不一樣，就是夾子沒夾好或板子沒放電乾淨，不要往下做。
4. 寫入改版映像，flashrom 會自動寫完再驗證：

   ```bash
   flashrom -p ch341a_spi -w X99-CH8_G3X99018_rebar_astgop.bin
   ```

   看到 `VERIFIED` 才算完成。
5. 拆夾子，接回電源開機。

Windows 下用 NeoProgrammer 或 AsProgrammer 也一樣：先 Read 存檔比對，再 Erase、Program、Verify。

## 用 flashrom 在 X99 本機刷（不用燒錄器）

flashrom.log 顯示 descriptor、BIOS、ME 三個區域都是 read-write，沒有 PR 保護範圍，BIOS Lock 預設關閉，所以可以直接在 X99 那台 Linux 上寫。

1. 先用 verbose 模式探測一次，不寫入：

   ```bash
   sudo flashrom -p internal -V 2>&1 | tee flashrom-probe.log
   ```

   確認輸出裡 `BIOS_CNTL` 的 BLE 和 SMM_BWP 是 0，沒有任何 `PR0` 到 `PR4` 的保護範圍，區域還是 read-write。有疑問就把 log 拿回來看。

2. 只寫 BIOS region，不碰 descriptor 和 ME：

   ```bash
   sudo flashrom -p internal --ifd -i bios -w X99-CH8_G3X99018_rebar_only.bin
   ```

   或直接刷 `X99-CH8_G3X99018_rebar_astgop.bin`，指令相同。

- 讀取時如果開機參數加了 `iomem=relaxed`，寫入時也要加。
- 看到 `VERIFIED` 才算完成，中途不要斷電。
- 兩個映像只改到 DXE volume 的空白區，但 0xB2F000 那個 4 KiB sector 會被整個重寫，它尾端有一點 CSM OpROM 容器資料。如果 flashrom 寫到一半報錯，不要重開機，立刻用同樣指令把 `dump1.bin` 寫回去。
- 寫完開不了機就只剩 CH341A 能救。沒有燒錄器的話，先刷 `rebar_only` 降低風險，或等燒錄器到手再刷。
- 不要寫整顆（不加 `--ifd -i bios`）。descriptor 寫壞比 BIOS 寫壞難救。
- 映像裡帶著 dump 當時的 NVRAM，刷完等於把 BIOS 設定回復到 dump 當時的狀態。

## 開機後的 BIOS 設定

1. 進 Setup，先 Load Optimized Defaults。改版後 NVRAM 可能被重建，重設一次最乾淨。
2. `Above 4G Decoding` 改成 `Enabled`。
3. `CSM Support` 改成 `Disabled`。如果想保留 CSM，至少把 CSM 下面的 `Video` 改成 `UEFI`。
4. 存檔重開。此時板載 VGA 的畫面由新加的 GOP 提供，有畫面就代表 GOP 成功。

## 設定 ReBAR 大小

ReBarDxe 要讀 NVRAM 裡的 `ReBarState` 變數才會動作，所以這步不能省。

Windows：

1. 以系統管理員執行 ReBarUEFI release 裡的 `ReBarState.exe`。
2. 輸入 `32`（不限制，給最大 BAR）。不行再試小一點，例如 `13` 是 8 GB。
3. 重開機，用 GPU-Z 看 `Resizable BAR` 是否 Enabled。

Linux：

```bash
printf '\x20' | sudo efivar -w -n a3c5b77a-c88f-4a93-bf1c-4a92a32c65ce-ReBarState -f /dev/stdin
# 重開後檢查
sudo lspci -vv | grep -i 'resizable bar' -A3
```

## 出問題時

| 狀況 | 處理 |
|---|---|
| 刷完開不了機，沒畫面 | 用 CH341A 寫回 `dump1.bin` |
| 關 CSM 後沒畫面 | 先用 CH341A 寫回 `dump1.bin`，或清 CMOS 讓 CSM 回到預設 Enabled |
| ReBarState.exe 報 `GetLastError: 5` | NVRAM 有寫入白名單，要再 patch NvramSmiDxe，回來找我 |
| BAR 開了但還是壓在 4G 以下 | 要針對 PciBus 寫專用 patch，回來找我 |

## 別做的事

- 不要在 QEMU VM 上跑任何 flashrom 寫入指令。
- 不要用 Windows 的 AFU 或 fpt 刷這個檔。可以刷，但刷壞就沒軟體能救，有 CH341A 就用 CH341A。
