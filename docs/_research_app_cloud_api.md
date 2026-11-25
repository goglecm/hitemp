<!-- Evidence extract. The summary and how it applies to this integration are in HW211_REGISTER_COMPARISON.md. -->

# Research dump: HiTemp / Aqua Temp / Linked-Go app & cloud API artifacts

**Status:** research only — do **not** merge into `HW211_REGISTER_COMPARISON.md` without review.  
**Product of interest:** `1245226668902080512` (HW211 DHW / Trianco S300 / Indol PV300 / Activair DHW / EvoHeat EVO270 family).  
**Written:** 2026-11-20  
**Method:** public web / GitHub / forums / MITM issue text only. No APK download, no paywalled binaries, no invented maps.  
**Cross-check:** adds only material **not** already covered (or only briefly footnoted) in:

- `docs/_research_hitemp_cloud.md`
- `docs/_research_foxair_phnix.md`
- `docs/_research_github_sweep.md`

---

## Executive verdict (O/S vs empty `getDataByCode`)

**Public evidence strongly supports client-side decode of packed words, not a second HiTemp API that returns named `O01`/`S01`.**

| Claim                                                                                      | Evidence                                                                               | Confidence                                      |
| ------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------- | ----------------------------------------------- |
| Named `O01`–`O06` / `S01`–`S06` stay empty on this product                                 | aquatemp #108; victor987; local guide; goglecm README                                  | **High** (already known)                        |
| Official **HiTemp iOS** poll list requests **`2050` + `2051`**, not `O01`–`O06` / any `S*` | aquatemp **#130** Proxyman capture (full 155-code list below)                          | **High — NEW detail**                           |
| App still shows compressor / heater / fan UI                                               | Same issue: app UI works while HA named O/S empty                                      | **High**                                        |
| Therefore app almost certainly **unpacks `2050`/`2051` locally**                           | Inference from poll list + empty named codes; **no JADX dump** of the decode published | **Medium–High**                                 |
| Second cloud host `cloud.go-heating.com`                                                   | openHAB AquaTemp binding + Reddit; **pool AquaTemp**, `appId` **14**                   | **High for pool**; **not shown for HiTemp DHW** |
| Device-side cache beyond heartbeat echo `1158`=`23205`                                     | No public Wireshark/Charles logs of a second upload path                               | **Not found**                                   |
| Heartbeat value variants other than `23205` / `0x5AA5`                                     | FoxAir + local only                                                                    | **None found**                                  |

---

## 1. What was already known (do not re-treat as new)

From prior dumps — referenced only for gap control:

- Endpoints on `cloud.linked-go.com:449/crmservice/api` (`login`, `getDataByCode`, `control`, device lists).
- Empty named O/S; live bits in **`2050`/`2051`** (vendor workbook + #108).
- Heartbeat: `control` with `protocolCode=app_heartbeat`, `value=23205`.
- FoxAir / WarmLink packing (`O01~023`@2019, `S01~S10`@2034) is a **different** board family.
- #130 Power write + `appId":"13"` (summary only in cloud dump).
- Package name `com.phinx.hitemp` exists on APK mirrors.

---

## 2. NEW — Full HiTemp iOS poll map (aquatemp #130)

**Source:** [radical-squared/aquatemp#130](https://github.com/radical-squared/aquatemp/issues/130) — Proxyman MITM of **HiTemp iOS v1.3.3**, EvoHeat EVO270-1 (same OEM product family as `1245…`).  
**Class:** observation (app traffic).

### 2.1 Control write (already summarised; kept for appId)

```json
{
  "param": [
    {
      "value": "0",
      "protocolCode": "Power",
      "deviceCode": "<redacted>"
    }
  ],
  "appId": "13"
}
```

- Integration wrongly wrote `mo6` (and often omitted `appId`).
- App never used `mo6` / `mode_real` / `R01: null` for simple power in that capture.

### 2.2 Periodic `getDataByCode` — 155 codes (full list)

**Body shape:** `{ "deviceCode", "appId": "13", "protocalCodes": [ … ] }`

```
Power, Mode, mode_real, 2050, M17, 1129, T10, T02, 1133, R01,
2011, 2012, 2013, 2014, M06, H07, L02, L03, L04, L06, L07, L08, L09,
L10, L11, L12, L13, M12, M13, M14, M15, M16, R03, R04, R05, R06, R07,
R08, R09, R10, R12, R14, R15, R17, R18, R19, R20, T01, T03, T04, T05,
T06, H98, /01, /02, D01, D02, D03, D04, D05, D06, D07, G01, G02, G03,
G04, E01, E02, E03, E04, E05, E06, H01, H03, H09, H16, H99, H30, H31,
H32, N01, N02, N03, N04, N05, N06, N07, N08, N09, N10, N11, O07, O08,
O09, R29, R30, C01, C02, C03, C06, C07, C08, C09, D10, D11, D12, D13,
R02, R11, R13, R16, L28, L29, F01, F02, F03, F04, F05, F06, F07, F08,
F09, F10, F11, F12, F13, T07, T08, T09, T20, T21, O25, O26, O27, O28,
O29, O18, O19, O21, O20, O22, O23, O24, 2051, L30, L31, L32, 1014, H02,
H15, H08, H06, H13, O03, Z03
```

### 2.3 O/S implications of this list (NEW analysis)

| Pattern                                             | Codes                                                    | Implication                                                                                        |
| --------------------------------------------------- | -------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| Packed status words requested                       | **`2050`, `2051`**                                       | App expects live O/S bits here                                                                     |
| Named compressor/heater/fan/switch codes **absent** | No `O01`, `O02`, `O04`, `O05`, `O06`; **no `S01`–`S06`** | App does **not** rely on named O/S from cloud                                                      |
| Odd exception                                       | **`O03`** alone among O01–O06                            | May be dead request, dual-use alias, or UI leftover — **unexplained** publicly                     |
| Scalars that _are_ named O                          | `O07`–`O09`, `O18`–`O29` (incl. `O25`–`O27`)             | Match victor “populated O except O01–O06” pattern                                                  |
| Heartbeat                                           | **Not** in this `getDataByCode` list                     | Live trigger is a separate `control` write (`app_heartbeat`); not captured in the posted poll body |

**Conclusion for the goal question:** the public MITM shows the official app reading the same packed registers integrations must decode. There is **no** public evidence of a parallel endpoint that returns filled `O01`/`S01` strings for this product.

---

## 3. NEW — `appId` map (13 vs 14 vs 16)

Prior dumps mentioned 13 (HiTemp #130) and 16 (WarmLink) in isolation. Combined public picture:

| `appId` | App / stack                        | Host                                     | Source                                                     |
| ------: | ---------------------------------- | ---------------------------------------- | ---------------------------------------------------------- |
|  **13** | **HiTemp** (iOS MITM)              | `cloud.linked-go.com:449/crmservice/api` | aquatemp **#130**                                          |
|  **14** | **AquaTemp** current Flutter app   | `cloud.go-heating.com/crmservice/api`    | openHAB binding `AquatempAuth.buildLoginRequest`           |
|  **16** | **WarmLink** / heating CRM scripts | `cloud.linked-go.com:449/crmservice/api` | aquatemp **#99**, VAdamec/WarmLink `APP_ID = "16"`, FoxAir |

**openHAB go-heating login body** ([`AquatempAuth.java`](https://github.com/rogrun/openhab-addons/blob/Release-AquaTemp-Binding-5.1.0.202610151811/bundles/org.openhab.binding.aquatemp/src/main/java/org/openhab/binding/aquatemp/internal/api/AquatempAuth.java)):

```json
{
  "userName": "<email>",
  "password": "<md5-hex>",
  "type": 2,
  "loginSource": "Flutter-Android",
  "areaCode": "en",
  "appId": 14
}
```

**Hosts enum** ([`AquatempApiType.java`](https://github.com/rogrun/openhab-addons/blob/Release-AquaTemp-Binding-5.1.0.202610151811/bundles/org.openhab.binding.aquatemp/src/main/java/org/openhab/binding/aquatemp/internal/api/AquatempApiType.java)):

| Config key  | Base URL                                                                         |
| ----------- | -------------------------------------------------------------------------------- |
| `linkedGo`  | `https://cloud.linked-go.com/cloudservice/api` (legacy pool path, **no** `:449`) |
| `goHeating` | `https://cloud.go-heating.com/crmservice/api`                                    |

**Relevance to HW211 DHW:** HiTemp captures still hit **linked-go `:449` + appId 13**. `go-heating` + appId **14** is a real second OEM cloud for **newer AquaTemp pool** accounts; **no public HiTemp DHW capture** on `go-heating.com` was found. Do not assume it populates named O/S for product `1245…`.

Local goglecm/hitemp `api.hi_temp.json` uses linked-go `:449` and does **not** embed `appId` in the static JSON (login body may omit it; #130 says the app always sends `13`).

---

## 4. NEW — Second API / host landscape

| Stack           | URL                                                      | Product family                                      | Register relevance                                 |
| --------------- | -------------------------------------------------------- | --------------------------------------------------- | -------------------------------------------------- |
| Legacy AquaTemp | `cloud.linked-go.com/cloudservice/api` (+ `.json` paths) | Pool (pre ~1.5.9)                                   | Different code sets; O01 often real on pool units  |
| CRM Linked-Go   | `cloud.linked-go.com:449/crmservice/api`                 | HiTemp DHW, WarmLink heating, newer AquaTemp-on-CRM | DHW uses `2050`; heating uses `O01~023`            |
| **Go Heating**  | `cloud.go-heating.com/crmservice/api`                    | Current AquaTemp pool Flutter app                   | openHAB + Reddit; **no DHW `1245…` map published** |

ioBroker “API level” taxonomy (forum script; still useful):

| Level | Meaning (script comments)  | Host used in script                                                          |
| ----: | -------------------------- | ---------------------------------------------------------------------------- |
|     1 | AquaTemp accounts ≤ v1.5.8 | linked-go `/cloudservice`                                                    |
|     2 | HiTemp accounts            | linked-go `/cloudservice` (older script) / CRM in practice for modern HiTemp |
|     3 | Newer AquaTemp             | linked-go `:449/crmservice` (MD5) — later apps also moved to **go-heating**  |

Reddit thread (2026-10): user asking how to auth to `cloud.go-heating.com` — no register dump; points to MITM / openHAB.

**PHNIX official app naming** ([phnix-e.com/technology](https://www.phnix-e.com/technology.html)):

- AQUA TEMP — pool
- AIWarmLink — heating & cooling
- Hitemp — domestic heat-pump water heaters

No public AIWarmLink JADX / parameter JSON for DHW `1245…` found.

---

## 5. APK / JADX / strings hunt

| Artifact                                                                                          | Result                                                                                                                             |
| ------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Package                                                                                           | `com.phinx.hitemp` (APKPure metadata; developer “Heater SoftWare Team”; versions cited in issues e.g. 1.3.3 / 1.3.7 / store 1.4.6) |
| Public JADX dumps / GitHub repos of decompiled HiTemp with `mode_real` / `2050` / `app_heartbeat` | **Not found**                                                                                                                      |
| Shared Wireshark / Charles `.pcap` / `.chls` with HiTemp bodies                                   | **Not found** beyond issue paste (#130 Proxyman text; #99 WarmLink curl)                                                           |
| Paywalled / mirror APK reverse                                                                    | **Skipped** per task rules                                                                                                         |

So: **no independent bit-packing table from the APK**; only MITM + workbook + HA entity JSON.

---

## 6. Parameter JSON / product maps (public)

Still concentrated in HA forks (already known lineage):

| File                                                        | Repo                                                                                          |
| ----------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| `entity_description.1245226668902080512.json` / `mapping.…` | radical-squared/aquatemp, goglecm/hitemp, forks                                               |
| WarmLink / Trianco heating product JSONs                    | arthuriansoft/aquatemp (`trianco`), zyznos321/warmlink, PR #105 product `1501438265440362496` |

**No new Trianco/Activair/Indol parameter JSON** beyond that family was located on the public web. App-shipped product catalogs (if they exist as remote downloads) are not mirrored in public repos.

ioBroker Midas script for product `1245226668902080512` still **requests named `O01`–`O06`/`S01`…** plus `1158`/`1159` — historical wrong assumption; does not prove those codes populate.

---

## 7. WeChat / Chinese OEM variants

| Item                                          | Finding                                                                                                               |
| --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| WeChat mini-program “PHNIX芬尼空气能”         | Exists (AppID partially public on WeChat radar sites); **no** Linked-Go register / `2050` / `O01` artifacts published |
| 芬尼 云集控                                   | Commercial multi-unit RS-485 + “phone mini-program”; not the HiTemp consumer cloud map                                |
| Gitee / Chinese blog dumps of HiTemp protocol | **Not found** in this pass                                                                                            |

---

## 8. Heartbeat `23205` variants

| Variant                                  | Found?                                                     |
| ---------------------------------------- | ---------------------------------------------------------- |
| `app_heartbeat` = **`23205`** (`0x5AA5`) | Yes — FoxAir tests/docs; local `1158` echo; goglecm consts |
| Other numeric heartbeat values           | **No** public source                                       |
| Heartbeat on go-heating.com              | **Not** documented in openHAB sources reviewed             |
| Heartbeat in #130 poll body              | Absent (expected — separate `control` call)                |

FoxAir note (already known): heartbeat `control` payload often **omits** `appId`; normal reads/writes use `appId` 16 on WarmLink.

---

## 9. Evidence about “device-side cache”

| Mechanism                                        | Public evidence                                                                                               |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------- |
| App open → DTU uploads live block                | Heartbeat write; FoxAir bus observation after heartbeat (heating); local `1158` tracks `23205` while app open |
| Cloud retains named O/S for DHW                  | Contradicted — values stay `''` even with live `2050`                                                         |
| Separate cache API / MQTT / WeChat push with O/S | **Not found**                                                                                                 |
| `tmJson` field on `getDataByCode` rows           | Present but **null/empty** for O codes (#108); not a packing map                                              |

---

## 10. Gaps still open

1. **No JADX / Flutter source** proving the exact bit→label mapping the HiTemp UI uses (must keep relying on workbook + observation).
2. Why the app still polls lone **`O03`** among O01–O06.
3. Whether HiTemp Android (`com.phinx.hitemp`) uses the same 155-code list and `appId` 13.
4. Whether any HiTemp account ever moved to **go-heating.com**.
5. Full #130 capture (author offered more) — only the poll list + Power write were pasted publicly.
6. No shared Charles/Wireshark archives beyond GitHub issue text.

---

## 11. Practical takeaway for integrations

For product `1245226668902080512`:

1. Treat empty named `O01`–`O06` / `S*` as **by design** on this cloud map.
2. Match the official app: poll **`2050`/`2051`** (and decode bits per `dtu_wifi` workbook).
3. Prefer **`appId: "13"`** on HiTemp CRM calls if the cloud starts enforcing it (WarmLink stays **16**; go-heating AquaTemp **14**).
4. Keep heartbeat = **`23205`** only; no public alternate.
5. Do **not** expect `cloud.go-heating.com` to solve DHW O/S unless a HiTemp capture appears.

---

## 12. Source URL index (this dump)

- https://github.com/radical-squared/aquatemp/issues/130 — HiTemp iOS MITM: Power/`appId` 13 + full 155-code poll including `2050`/`2051`
- https://github.com/radical-squared/aquatemp/issues/108 — empty O/S; `2050` examples
- https://github.com/radical-squared/aquatemp/issues/99 — WarmLink `appId` 16 + heating code list
- https://github.com/VAdamec/WarmLink/blob/main/custom_components/warmlink/const.py — `APP_ID = "16"`
- https://github.com/rogrun/openhab-addons/blob/Release-AquaTemp-Binding-5.1.0.202610151811/bundles/org.openhab.binding.aquatemp/src/main/java/org/openhab/binding/aquatemp/internal/api/AquatempApiType.java — linked-go vs go-heating hosts
- https://github.com/rogrun/openhab-addons/blob/Release-AquaTemp-Binding-5.1.0.202610151811/bundles/org.openhab.binding.aquatemp/src/main/java/org/openhab/binding/aquatemp/internal/api/AquatempAuth.java — go-heating login + **`appId` 14**
- https://community.openhab.org/t/aquatemp-binding-5-0-0-0-5-9-9-9/165377 — go-heating support announcement
- https://forum.iobroker.net/topic/54765/javascript-midas-aquatemp-poolheizung — API levels; product `1245…` still requests named O/S
- https://www.phnix-e.com/technology.html — AQUA TEMP / AIWarmLink / Hitemp app split
- https://apkpure.net/hitemp/com.phinx.hitemp — package metadata only (no reverse)
- https://www.reddit.com/r/homeautomation/comments/1x9roe5/i_have_a_heatpump_that_connects_to/ — go-heating auth question (no register dump)
