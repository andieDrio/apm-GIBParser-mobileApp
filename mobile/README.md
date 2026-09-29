# Android Mobile Client

Native Kotlin + Jetpack Compose client for the Group-IB Mobile Threat Intelligence Reporter.

## Toolchain baseline

- Android Gradle Plugin: 9.4.0
- Kotlin: 2.4.10
- Gradle: 9.6.0 or compatible Android Studio-managed Gradle
- compileSdk / targetSdk: 37
- Java: 17
- Compose BOM: 2026.09.00

## Build

Open the repository root in Android Studio and allow Gradle sync.

For CLI validation, use a Gradle 9.6.0 installation or generate the Gradle Wrapper:

    gradle wrapper --gradle-version 9.6.0
    ./gradlew :mobile:assembleDebug
    ./gradlew :mobile:test

## Device validation

With an HONOR X9c connected and authorized:

    ./gradlew :mobile:installDebug
    adb shell am start -n com.apm.gibmobile/.MainActivity

The device must reach the backend through HTTPS. The app intentionally rejects HTTP backend URLs and Android cleartext traffic is disabled.

## Functional validation

1. Configure the HTTPS backend URL under Settings.
2. Generate a report with GENERATE GIB REPORT.
3. Confirm run progress reaches SUCCEEDED.
4. Confirm the report PDF is retrieved.
5. Validate VIEW REPORT.
6. Validate SHARE PDF.
7. Validate SAVE PDF through the Android system document picker.
8. Open History and download an existing successful report.
9. Confirm no Group-IB credential is displayed or stored by the mobile client.

The mobile client never calls Group-IB directly.