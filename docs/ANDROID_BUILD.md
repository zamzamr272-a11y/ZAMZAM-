# Android APK build and installation

## How the Android app is packaged

The Android app is a native Java Activity that embeds the responsive frontend through Android WebView. The app loads its bundled assets from `https://appassets.androidplatform.net/assets/www/index.html` with AndroidX `WebViewAssetLoader`; it does not use a permissive universal `file://` origin. The backend remains a separately deployed online service.

The project uses compile/target SDK 36, minimum SDK 26, Java 17, Android Gradle Plugin 8.13.2, Gradle 8.13 and AndroidX WebKit 1.17.1.

## Build locally

Requirements: JDK 17, Android SDK platform 36/build-tools 36.0.0 and Gradle 8.13.

```bash
mkdir -p android/app/src/main/assets/www
cp -a frontend/. android/app/src/main/assets/www/
cd android
gradle --no-daemon :app:assembleDebug
```

Output:

```text
android/app/build/outputs/apk/debug/app-debug.apk
```

Debug package uses application ID suffix `.debug`. For local-only HTTP backend testing, run Gradle with `ALLOW_CLEARTEXT=true` (debug variant only); never publish that build. Production release rejects cleartext HTTP and requires HTTPS.

## GitHub Actions: debug APK

Workflow: `.github/workflows/android-apk.yml`.

1. Create an empty repository and push the complete NEXORA project to its root, including the `.github/workflows` directory.
2. Enable GitHub Actions in repository settings.
3. Push a commit touching `android/**` or `frontend/**`, or open **Actions → Build Android APK → Run workflow**.
4. Wait for successful `debug-apk` job.
5. Download artifact `NEXORA-Android-debug-APK`, extract it and install `app-debug.apk` on an Android test device. On some devices, allow installing apps from the browser/file manager used to open the APK.

The workflow installs JDK 17, Gradle 8.13 and Android SDK 36, copies frontend files into app assets, builds `:app:assembleDebug` and uploads the APK artifact for 14 days.

## Signed release APK (optional)

Only the keystore owner should create and retain the signing key. Generate a release keystore securely on a trusted workstation; never commit the keystore file or passwords. Convert the keystore to a Base64 string and store the following GitHub Actions secrets:

- `ANDROID_KEYSTORE_BASE64`
- `ANDROID_KEYSTORE_PASSWORD`
- `ANDROID_KEY_ALIAS`
- `ANDROID_KEY_PASSWORD`

Run **Actions → Build Android APK → Run workflow**, set `signed_release=true`, and start the run. The job checks that every secret is present, writes the decoded keystore under the GitHub runner temporary directory, signs `assembleRelease`, and uploads `NEXORA-Android-signed-release-APK`. The keystore is not copied into the artifact or repository.

Store encrypted offline backup copies of the keystore and passwords. Losing the signing key may prevent publishing future updates to the same Android application identity. Before public distribution, set permanent versionCode/versionName and application ID, enable and validate R8/minification, inspect permissions and exported components, and verify the signed artifact on real devices.

## API/backend configuration after installation

APK does not contain the API server or database. Deploy the backend first, configure HTTPS and add `https://appassets.androidplatform.net` to `CORS_ORIGINS`. In the installed app, open **Hubungkan/konfigurasi** and provide:

```text
https://api.your-domain.example/api/v1
```

For Android emulator development, use `http://10.0.2.2:8000/api/v1`; the debug cleartext build must be generated with `ALLOW_CLEARTEXT=true`. For a physical device on a private network, use the reachable server LAN IP only for development. Do not use public HTTP.

## Build limitations

The package-preparation environment did not have Android SDK, Gradle or a physical device. The first verified compilation should be the GitHub Actions run after the repository is pushed. A workflow file is a build recipe, not evidence that an APK already exists.
