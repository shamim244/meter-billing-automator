# Reverse-Engineering Findings & Camera Injection Analysis

This document details source-level findings from decompiled APKs and technical evaluations for static image camera injection.

---

## 1. App 1 Internals (`in.phoenix.bpdcl` / `bpdcl.apk`)

Decompiled via `jadx` $\to$ `extracted/BillingManual.java` (20,842 lines).

### Key Source References:
- **Button Listener Initialization (Line 8191):**
  ```java
  this.KwhCaptureButton.setOnClickListener(new View.OnClickListener() {
      public void onClick(View view) {
          if (BillingManual.this.validateObsAndMeterLocType()) {
              if (BillingManual.this.ocrAgency.equalsIgnoreCase("Coral")) {
                  BillingManual.this.callCameraIntentForCoral(...);
              }
          }
      }
  });
  ```
- **Coral Intent Dispatcher (Line 14684):**
  ```java
  Intent intent = new Intent();
  intent.setAction("android.intent.action.SEND");
  intent.setType("bsmr/meter");
  intent.setPackage("in.coral.bpdcl");
  intent.putExtra("BOARD_CODE", BuildConfig.APP_NAME);
  intent.putExtra("ACCESS_KEY", "5iVFQs34Qm_nbpdcl");
  intent.putExtra("CONSUMER_NO", billingMasterVO.getConsumerNo());
  ...
  BillingManual.this.startActivityForResult(intent, BillingManual.CAMERA_REQUEST);
  ```
- **Signature Check:** **None**. App 1 does not inspect package certificates or integrity signatures of `in.coral.bpdcl`. Any app responding to `bsmr/meter` with `action="SEND"` can fulfill the contract.
- **Submit Button (Line 5101 & 8322):**
  `this.submit = (Button) findViewById(R.id.Submit);` triggers `AnonymousClass135`, which calculates bill components and persists data into the SQLite database table `ONLINE_BILL_IMAGES`.

---

## 2. App 2 Internals (`in.coral.bpdcl` / `coral.apk`)

Pulled from `/data/app/` $\to$ `ScanMeterActivity.java` (3,456 lines).

### Key Architectural Findings:
- **Camera Stack:** Built on Google AndroidX **CameraX** library (`androidx.camera.view.PreviewView`, `ImageCapture`, `ImageAnalysis`).
- **Vision Engine:** Google **ML Kit Vision** (`com.google.android.gms.internal.mlkit_vision_text_common.zzun`, barcode & OCR modules).
- **Capture Trigger (`ScanMeterActivity.n.a()`):**
  ```java
  public final void a() {
      scanMeterActivity.L = in.coral.bpdcl.util.a.d("meter_uf", "bigImg");
      scanMeterActivity.M = in.coral.bpdcl.util.a.d("meter_dept", "deptImg");
      scanMeterActivity.F0.J(scanMeterActivity.F, new u1(scanMeterActivity));
  }
  ```
  Where:
  - `F0` is the `androidx.camera.core.ImageCapture` instance.
  - `F0.J(..., u1)` is the obfuscated call to `ImageCapture.takePicture(...)`.
  - `L` and `M` are the local JPEG output files (`meter_uf` and `meter_dept`).
  - `u1` is the `OnImageSavedCallback` which passes the saved photo to the ML Kit OCR processor.

---

## 3. Technical Evaluation: Static Image Injection onto Camera

Can a static image be fed into the camera instead of pointing at a physical meter?

### Feasibility Summary:
| Approach | Feasibility | Root Required | App Mod Required | Risk / Notes |
| :--- | :--- | :--- | :--- | :--- |
| **1. Screen Display (Monitor/Phone)** | **100% (Immediate)** | No | No | Easiest zero-risk method; adjust brightness & zoom |
| **2. PC Android Emulator + OBS** | **100% (Automated)** | No | No | Map OBS Virtual Camera to Emulator webcam; feeds perfect digital frames |
| **3. Virtual Android (VMOS/VPhoneGaga)** | **100% (On-Device)** | No (uses VM root) | No | Virtual camera module runs inside isolated container on phone |
| **4. LSPosed Virtual Camera (Magisk)** | **100%** | Yes (Host root) | No | Device is currently unrooted (`no_su`); requires bootloader unlock |
| **5. APK Smali Patching (`coral.apk`)** | **High** | No | Yes | Patch `ScanMeterActivity` to copy `/sdcard/meter.jpg` to `L`/`M` instead of CameraX `takePicture` |

### Smali Patching Blueprint (for Option 5):
If patching `in.coral.bpdcl`:
1. Modify `ScanMeterActivity$n.smali` where `F0.J()` is called.
2. Replace with a file copy from `/sdcard/Download/meter_feed.jpg` directly into `scanMeterActivity.L` and `scanMeterActivity.M`.
3. Directly invoke the success callback `u1.onImageSaved()`.
4. Recompile with `apktool`, sign with `uber-apk-signer`, and reinstall via `adb install -r`.
