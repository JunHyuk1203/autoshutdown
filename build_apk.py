import os
import shutil
import subprocess

def create_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    base_dir = r"c:\Users\tntdr\.gemini\antigravity-ide\scratch\auto_shutdown\AndroidApp"
    os.makedirs(base_dir, exist_ok=True)

    android_sdk = os.environ.get("ANDROID_HOME", os.path.join(os.environ["LOCALAPPDATA"], "Android", "Sdk"))
    create_file(os.path.join(base_dir, 'local.properties'), "sdk.dir=" + android_sdk.replace(chr(92), "/") + chr(10))

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
rootProject.name = "SmartPowerApp"
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

    # app/build.gradle
    create_file(os.path.join(base_dir, 'app', 'build.gradle'), """
plugins {
    id 'com.android.application'
}

android {
    namespace 'com.smartpower.app'
    compileSdk 34

    defaultConfig {
        applicationId "com.smartpower.app"
        minSdk 24
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
}
""")

    # AndroidManifest.xml
    create_file(os.path.join(base_dir, 'app', 'src', 'main', 'AndroidManifest.xml'), """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <uses-permission android:name="android.permission.INTERNET" />

    <application
        android:allowBackup="false"
        android:usesCleartextTraffic="false"
        android:label="SmartPower"
        android:supportsRtl="true"
        android:theme="@style/Theme.AppCompat.Light.NoActionBar">
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
    create_file(os.path.join(base_dir, 'app', 'src', 'main', 'java', 'com', 'smartpower', 'app', 'MainActivity.java'), """package com.smartpower.app;

import android.annotation.SuppressLint;
import android.os.Bundle;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import androidx.appcompat.app.AppCompatActivity;

public class MainActivity extends AppCompatActivity {
    private WebView webView;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        webView = new WebView(this);
        setContentView(webView);

        WebSettings webSettings = webView.getSettings();
        webSettings.setJavaScriptEnabled(true);
        webSettings.setDomStorageEnabled(true);
        webSettings.setAllowContentAccess(false);
        webSettings.setAllowFileAccessFromFileURLs(false);
        webSettings.setAllowUniversalAccessFromFileURLs(false);
        webSettings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, android.webkit.WebResourceRequest request) {
                return !"file:///android_asset/dashboard.html".equals(request.getUrl().toString());
            }
        });
        webView.loadUrl("file:///android_asset/dashboard.html");
    }

    @Override
    public void onBackPressed() {
        if(webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
""")

    # copy dashboard.html
    src_html = r"c:\Users\tntdr\.gemini\antigravity-ide\scratch\auto_shutdown\dashboard.html"
    dst_assets = os.path.join(base_dir, 'app', 'src', 'main', 'assets')
    os.makedirs(dst_assets, exist_ok=True)
    shutil.copy(src_html, os.path.join(dst_assets, 'dashboard.html'))

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

    print("Building APK...")
    process = subprocess.Popen([gradle_bat, "assembleDebug"], cwd=base_dir, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in process.stdout:
        print(line, end='')

    process.wait()
    if process.returncode == 0:
        apk_src = os.path.join(base_dir, 'app', 'build', 'outputs', 'apk', 'debug', 'app-debug.apk')
        apk_dst = r"c:\Users\tntdr\.gemini\antigravity-ide\scratch\auto_shutdown\SmartPowerDashboard.apk"
        shutil.copy(apk_src, apk_dst)
        print("APK build successful: SmartPowerDashboard.apk")
    else:
        raise SystemExit(process.returncode)

if __name__ == "__main__":
    main()
