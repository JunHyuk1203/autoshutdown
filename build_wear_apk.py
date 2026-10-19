import os
import shutil
import subprocess

def create_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    base_dir = r"c:\Users\tntdr\.gemini\antigravity-ide\scratch\auto_shutdown\AndroidWearApp"
    os.makedirs(base_dir, exist_ok=True)

    # settings.gradle
    create_file(os.path.join(base_dir, 'settings.gradle'), """
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}
rootProject.name = "SmartPowerWearApp"
include ':app'
""")

    # build.gradle
    create_file(os.path.join(base_dir, 'build.gradle'), """
buildscript {
    repositories {
        google()
        mavenCentral()
    }
    dependencies {
        classpath "com.android.tools.build:gradle:8.5.0"
    }
}
""")

    # gradle.properties
    create_file(os.path.join(base_dir, 'gradle.properties'), """
android.useAndroidX=true
""")

    android_sdk = os.environ.get("ANDROID_HOME", os.path.join(os.environ["LOCALAPPDATA"], "Android", "Sdk"))
    create_file(os.path.join(base_dir, 'local.properties'), "sdk.dir=" + android_sdk.replace(chr(92), "/") + chr(10))

    # app/build.gradle
    create_file(os.path.join(base_dir, 'app', 'build.gradle'), """
plugins {
    id 'com.android.application'
}

android {
    namespace 'com.smartpower.wear'
    compileSdk 34

    defaultConfig {
        applicationId "com.smartpower.wear"
        minSdk 26
        targetSdk 34
        versionCode 1
        versionName "1.0"
    }

    buildTypes {
        release {
            minifyEnabled false
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
        }
    }
    compileOptions {
        sourceCompatibility JavaVersion.VERSION_17
        targetCompatibility JavaVersion.VERSION_17
    }
}

dependencies {
    implementation 'androidx.appcompat:appcompat:1.6.1'
    implementation 'com.google.android.gms:play-services-wearable:18.1.0'
}
""")

    # AndroidManifest.xml
    create_file(os.path.join(base_dir, 'app', 'src', 'main', 'AndroidManifest.xml'), """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <uses-feature android:name="android.hardware.type.watch" />
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.WAKE_LOCK" />

    <application
        android:allowBackup="false"
        android:usesCleartextTraffic="false"
        android:label="SmartPower"
        android:supportsRtl="true"
        android:theme="@style/Theme.AppCompat.Light.NoActionBar">
        <meta-data
            android:name="com.google.android.wearable.standalone"
            android:value="true" />

        <activity
            android:name=".MainActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>

</manifest>
""")

    # MainActivity.java
    create_file(os.path.join(base_dir, 'app', 'src', 'main', 'java', 'com', 'smartpower', 'wear', 'MainActivity.java'), """package com.smartpower.wear;

import android.app.AlertDialog;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import org.json.JSONObject;

import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

public class MainActivity extends AppCompatActivity {

    private SharedPreferences prefs;
    private String dbUrl = "https://atss-a1f9e-default-rtdb.firebaseio.com/";
    private String authKey = "";
    private TextView statusText;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        prefs = getSharedPreferences("SmartPowerWear", MODE_PRIVATE);
        dbUrl = prefs.getString("dbUrl", "https://atss-a1f9e-default-rtdb.firebaseio.com/");
        try {
            String legacy = prefs.getString("authKey", "");
            authKey = legacy.isEmpty() ? decryptToken(prefs.getString("protectedAuthKey", "")) : legacy;
            prefs.edit().putString("protectedAuthKey", encryptToken(authKey)).remove("authKey").apply();
        } catch (Exception e) {
            authKey = "";
        }

        ScrollView scrollView = new ScrollView(this);
        scrollView.setPadding(30, 80, 30, 80);
        scrollView.setClipToPadding(false);

        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setGravity(android.view.Gravity.CENTER_HORIZONTAL);
        scrollView.addView(layout);

        TextView titleText = new TextView(this);
        titleText.setText("⚡ SmartPower");
        titleText.setTextSize(20);
        titleText.setGravity(android.view.Gravity.CENTER);
        titleText.setPadding(0, 0, 0, 20);
        layout.addView(titleText);

        statusText = new TextView(this);
        statusText.setText("대기 중...");
        statusText.setGravity(android.view.Gravity.CENTER);
        statusText.setPadding(0, 0, 0, 40);
        layout.addView(statusText);

        Button btnShutdown = new Button(this);
        btnShutdown.setText("전체 종료");
        btnShutdown.setBackgroundColor(0xFFFF4444);
        btnShutdown.setTextColor(0xFFFFFFFF);
        btnShutdown.setOnClickListener(v -> confirmAndSend("shutdown", "전체 종료"));
        setBtnMargin(btnShutdown);
        layout.addView(btnShutdown);

        Button btnRestart = new Button(this);
        btnRestart.setText("전체 재부팅");
        btnRestart.setBackgroundColor(0xFF33B5E5);
        btnRestart.setTextColor(0xFFFFFFFF);
        btnRestart.setOnClickListener(v -> confirmAndSend("restart", "전체 재부팅"));
        setBtnMargin(btnRestart);
        layout.addView(btnRestart);

        Button btnWOL = new Button(this);
        btnWOL.setText("전체 켜기 (WOL)");
        btnWOL.setBackgroundColor(0xFF00C851);
        btnWOL.setTextColor(0xFFFFFFFF);
        btnWOL.setOnClickListener(v -> confirmAndSend("wol", "전체 켜기"));
        setBtnMargin(btnWOL);
        layout.addView(btnWOL);

        Button btnSetup = new Button(this);
        btnSetup.setText("설정 (URL)");
        btnSetup.setOnClickListener(v -> showSetupDialog());
        setBtnMargin(btnSetup);
        layout.addView(btnSetup);

        setContentView(scrollView);
    }

    private void setBtnMargin(Button btn) {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        params.setMargins(10, 10, 10, 10);
        btn.setLayoutParams(params);
    }

    private void confirmAndSend(String action, String label) {
        new AlertDialog.Builder(this)
                .setTitle(label)
                .setMessage("정말로 " + label + " 명령을 실행하시겠습니까?")
                .setPositiveButton("실행", (dialog, which) -> sendCommand(action))
                .setNegativeButton("취소", null)
                .show();
    }

    private void sendCommand(String action) {
        statusText.setText("전송 중...");
        new Thread(() -> {
            try {
                if (!dbUrl.equals("https://atss-a1f9e-default-rtdb.firebaseio.com/") || authKey.isEmpty()) {
                    throw new SecurityException("HTTPS Firebase URL and administrator ID token required");
                }
                String urlStr = dbUrl;
                if (!urlStr.endsWith("/")) urlStr += "/";
                urlStr += "commands/__ALL__.json";
                if (!authKey.isEmpty()) {
                    urlStr += "?auth=" + java.net.URLEncoder.encode(authKey, "UTF-8");
                }

                URL url = new URL(urlStr);
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setConnectTimeout(10000);
                conn.setReadTimeout(10000);
                conn.setInstanceFollowRedirects(false);
                conn.setRequestMethod("PUT");
                conn.setRequestProperty("Content-Type", "application/json");
                conn.setDoOutput(true);

                JSONObject payload = new JSONObject();
                payload.put("action", action);
                payload.put("message", "");
                payload.put("timestamp", System.currentTimeMillis() / 1000.0);

                OutputStream os = conn.getOutputStream();
                os.write(payload.toString().getBytes("UTF-8"));
                os.close();

                int code = conn.getResponseCode();
                new Handler(Looper.getMainLooper()).post(() -> {
                    if (code >= 200 && code < 300) {
                        statusText.setText("성공!");
                        Toast.makeText(this, "성공적으로 전송됨", Toast.LENGTH_SHORT).show();
                    } else {
                        statusText.setText("오류: " + code);
                    }
                });

            } catch (Exception e) {
                new Handler(Looper.getMainLooper()).post(() -> {
                    statusText.setText("오류 발생");
                    Toast.makeText(this, e.getMessage(), Toast.LENGTH_LONG).show();
                });
            }
        }).start();
    }

    private javax.crypto.SecretKey tokenKey() throws Exception {
        java.security.KeyStore store = java.security.KeyStore.getInstance("AndroidKeyStore");
        store.load(null);
        if (!store.containsAlias("SmartPowerToken")) {
            javax.crypto.KeyGenerator generator = javax.crypto.KeyGenerator.getInstance("AES", "AndroidKeyStore");
            generator.init(new android.security.keystore.KeyGenParameterSpec.Builder("SmartPowerToken", 3)
                .setBlockModes("GCM").setEncryptionPaddings("NoPadding").build());
            generator.generateKey();
        }
        return (javax.crypto.SecretKey) store.getKey("SmartPowerToken", null);
    }

    private String encryptToken(String token) throws Exception {
        if (token.isEmpty()) return "";
        javax.crypto.Cipher cipher = javax.crypto.Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(javax.crypto.Cipher.ENCRYPT_MODE, tokenKey());
        return android.util.Base64.encodeToString(cipher.getIV(), 2) + ":" +
            android.util.Base64.encodeToString(cipher.doFinal(token.getBytes("UTF-8")), 2);
    }

    private String decryptToken(String token) throws Exception {
        if (token.isEmpty()) return "";
        String[] parts = token.split(":", 2);
        javax.crypto.Cipher cipher = javax.crypto.Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(javax.crypto.Cipher.DECRYPT_MODE, tokenKey(),
            new javax.crypto.spec.GCMParameterSpec(128, android.util.Base64.decode(parts[0], 2)));
        return new String(cipher.doFinal(android.util.Base64.decode(parts[1], 2)), "UTF-8");
    }

    private void showSetupDialog() {
        AlertDialog.Builder builder = new AlertDialog.Builder(this);
        builder.setTitle("DB URL 설정");

        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(20, 20, 20, 20);

        final EditText inputUrl = new EditText(this);
        inputUrl.setText(dbUrl);
        inputUrl.setHint("Database URL");
        layout.addView(inputUrl);

        final EditText inputKey = new EditText(this);
        inputKey.setText(authKey);
        inputKey.setHint("Firebase 관리자 ID 토큰");
        inputKey.setInputType(129);
        layout.addView(inputKey);

        builder.setView(layout);

        builder.setPositiveButton("저장", (dialog, which) -> {
            dbUrl = inputUrl.getText().toString();
            authKey = inputKey.getText().toString();
            try {
                prefs.edit().putString("dbUrl", dbUrl).putString("protectedAuthKey", encryptToken(authKey)).remove("authKey").apply();
            } catch (Exception e) {
                Toast.makeText(this, "인증정보 암호화 실패", Toast.LENGTH_SHORT).show();
                return;
            }
            Toast.makeText(this, "저장됨", Toast.LENGTH_SHORT).show();
        });
        builder.setNegativeButton("취소", null);
        builder.show();
    }
}
""")

    # Run gradle build
    gradle_bat = os.environ.get("SMARTPOWER_GRADLE")
    if not gradle_bat:
        import glob
        candidates = glob.glob(os.path.expanduser(r"~/.gradle/wrapper/dists/gradle-8.9-bin/*/gradle-8.9/bin/gradle.bat"))
        candidates += glob.glob(os.path.join(os.path.dirname(__file__), ".security-build", "tools", "gradle-8.9", "bin", "gradle.bat"))
        if not candidates:
            raise RuntimeError("Gradle 8.9 is required. Set SMARTPOWER_GRADLE to gradle.bat.")
        gradle_bat = candidates[0]
    jbr_path = r"C:\Program Files\Android\Android Studio\jbr"

    env = os.environ.copy()
    env["JAVA_HOME"] = jbr_path

    print("Building Wear APK...")
    process = subprocess.Popen([gradle_bat, "assembleDebug"], cwd=base_dir, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in process.stdout:
        print(line, end='')

    process.wait()
    if process.returncode == 0:
        apk_src = os.path.join(base_dir, 'app', 'build', 'outputs', 'apk', 'debug', 'app-debug.apk')
        apk_dst = r"c:\Users\tntdr\.gemini\antigravity-ide\scratch\auto_shutdown\SmartPowerWear.apk"
        shutil.copy(apk_src, apk_dst)
        print("APK build successful: SmartPowerWear.apk")
    else:
        raise SystemExit(process.returncode)

if __name__ == "__main__":
    main()
