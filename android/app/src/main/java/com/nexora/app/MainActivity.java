package com.nexora.app;

import android.app.Activity;
import android.Manifest;
import android.content.pm.PackageManager;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.CookieManager;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceError;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.WebResourceResponse;
import android.graphics.Bitmap;
import android.graphics.Insets;
import android.os.Build;
import android.view.WindowInsets;
import android.view.View;
import android.view.WindowManager;
import android.widget.FrameLayout;
import android.widget.ProgressBar;
import android.widget.Toast;
import android.webkit.ValueCallback;
import android.webkit.JavascriptInterface;
import androidx.webkit.WebViewAssetLoader;
import org.json.JSONObject;
import java.util.ArrayList;



public class MainActivity extends Activity {
    private WebView webView;
    private WebViewAssetLoader assetLoader;
    private ProgressBar progressBar;
    private ValueCallback<Uri[]> fileCallback;
    private SpeechRecognizer speechRecognizer;
    private boolean speechStartPending = false;
    private static final int REQUEST_RECORD_AUDIO = 702;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(android.graphics.Color.rgb(11, 17, 23));
        getWindow().setNavigationBarColor(android.graphics.Color.rgb(11, 17, 23));
        getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);

        FrameLayout root = new FrameLayout(this);
        // Android 15+ enforces edge-to-edge for modern target SDKs. Apply the
        // system-bar insets to the root container so controls remain tappable.
        root.setOnApplyWindowInsetsListener((view, insets) -> {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                Insets bars = insets.getInsets(WindowInsets.Type.systemBars());
                view.setPadding(bars.left, bars.top, bars.right, bars.bottom);
            } else {
                view.setPadding(insets.getSystemWindowInsetLeft(), insets.getSystemWindowInsetTop(),
                        insets.getSystemWindowInsetRight(), insets.getSystemWindowInsetBottom());
            }
            return insets;
        });
        webView = new WebView(this);
        progressBar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progressBar.setMax(100);
        progressBar.setProgressTintList(android.content.res.ColorStateList.valueOf(android.graphics.Color.rgb(66, 214, 197)));
        progressBar.setBackgroundColor(android.graphics.Color.rgb(17, 27, 36));
        root.addView(webView, new FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));
        FrameLayout.LayoutParams progressParams = new FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, dp(3));
        root.addView(progressBar, progressParams);
        setContentView(root);
        root.requestApplyInsets();

        assetLoader = new WebViewAssetLoader.Builder()
                .setDomain("appassets.androidplatform.net")
                .addPathHandler("/assets/", new WebViewAssetLoader.AssetsPathHandler(this))
                .build();

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        webView.addJavascriptInterface(new VoiceBridge(), "NexoraNative");
        settings.setDatabaseEnabled(true);
        // All app content is served via WebViewAssetLoader under a secure HTTPS-like
        // origin. The WebView does not need broad file/content URL access.
        settings.setAllowFileAccess(false);
        // The user-selected document picker returns content:// URIs; WebView needs
        // content access to read only the selected upload. file:// access stays off.
        settings.setAllowContentAccess(true);
        settings.setAllowFileAccessFromFileURLs(false);
        settings.setAllowUniversalAccessFromFileURLs(false);
        settings.setMixedContentMode(BuildConfig.DEBUG
                ? WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE
                : WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setJavaScriptCanOpenWindowsAutomatically(false);
        settings.setSupportMultipleWindows(false);
        settings.setSafeBrowsingEnabled(true);
        settings.setMediaPlaybackRequiresUserGesture(true);
        settings.setTextZoom(100);
        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(webView, false);

        webView.setOverScrollMode(View.OVER_SCROLL_NEVER);
        webView.setBackgroundColor(android.graphics.Color.rgb(11, 17, 23));
        webView.setWebViewClient(new WebViewClient() {
            @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                return assetLoader.shouldInterceptRequest(request.getUrl());
            }

            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                String scheme = uri.getScheme() == null ? "" : uri.getScheme();
                if ("file".equals(scheme) || "https".equals(scheme) || "http".equals(scheme)) {
                    String url = uri.toString();
                    if (url.startsWith("https://appassets.androidplatform.net/assets/")) return false;
                    if (url.startsWith("http://10.0.2.2:") || url.startsWith("http://localhost:")) return false;
                    if ("http".equals(scheme) || "https".equals(scheme)) {
                        try { startActivity(new Intent(Intent.ACTION_VIEW, uri)); } catch (Exception ignored) {}
                        return true;
                    }
                }
                try { startActivity(new Intent(Intent.ACTION_VIEW, uri)); } catch (Exception ignored) {}
                return true;
            }
            @Override public void onPageStarted(WebView view, String url, Bitmap favicon) {
                progressBar.setVisibility(View.VISIBLE); progressBar.setProgress(10);
            }
            @Override public void onPageFinished(WebView view, String url) {
                progressBar.setProgress(100); progressBar.setVisibility(View.GONE);
            }
            @Override public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) Toast.makeText(MainActivity.this, "NEXORA gagal memuat layar. Coba buka ulang aplikasi.", Toast.LENGTH_LONG).show();
            }
        });
        webView.setWebChromeClient(new WebChromeClient() {
            @Override public void onProgressChanged(WebView view, int newProgress) {
                progressBar.setProgress(newProgress);
                progressBar.setVisibility(newProgress < 100 ? View.VISIBLE : View.GONE);
            }
            @Override public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback, FileChooserParams params) {
                if (fileCallback != null) fileCallback.onReceiveValue(null);
                fileCallback = callback;
                Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
                intent.addCategory(Intent.CATEGORY_OPENABLE);
                intent.setType("*/*");
                intent.putExtra(Intent.EXTRA_MIME_TYPES, new String[]{"image/jpeg", "image/png", "application/pdf"});
                intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, false);
                try { startActivityForResult(intent, 701); }
                catch (Exception e) { fileCallback = null; Toast.makeText(MainActivity.this, "Pemilih file tidak tersedia.", Toast.LENGTH_SHORT).show(); return false; }
                return true;
            }
        });

        webView.loadUrl("https://appassets.androidplatform.net/assets/www/index.html");
    }

    private final class VoiceBridge {
        @JavascriptInterface public void start() {
            runOnUiThread(() -> {
                if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
                    speechStartPending = true;
                    requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, REQUEST_RECORD_AUDIO);
                    return;
                }
                startSpeechRecognition();
            });
        }
        @JavascriptInterface public void stop() {
            runOnUiThread(() -> {
                speechStartPending = false;
                if (speechRecognizer != null) {
                    try { speechRecognizer.stopListening(); } catch (Exception ignored) {}
                }
            });
        }
    }

    private void startSpeechRecognition() {
        if (!SpeechRecognizer.isRecognitionAvailable(this)) {
            sendVoiceError("Layanan pengenalan suara Bahasa Indonesia tidak tersedia pada perangkat ini.");
            return;
        }
        try {
            if (speechRecognizer != null) { speechRecognizer.destroy(); speechRecognizer = null; }
            speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this);
            speechRecognizer.setRecognitionListener(new RecognitionListener() {
                @Override public void onReadyForSpeech(Bundle params) {}
                @Override public void onBeginningOfSpeech() {}
                @Override public void onRmsChanged(float rmsdB) {}
                @Override public void onBufferReceived(byte[] buffer) {}
                @Override public void onEndOfSpeech() {}
                @Override public void onError(int error) {
                    String message = error == SpeechRecognizer.ERROR_NO_MATCH ? "Ucapan tidak terbaca. Coba bicara lebih jelas." :
                        error == SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS ? "Izin mikrofon tidak diberikan." :
                        error == SpeechRecognizer.ERROR_RECOGNIZER_BUSY ? "Layanan suara sedang sibuk. Coba lagi." :
                        "Pengenalan suara gagal. Coba lagi atau masukkan transaksi secara manual.";
                    sendVoiceError(message);
                }
                @Override public void onResults(Bundle results) {
                    ArrayList<String> matches = results == null ? null : results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
                    if (matches != null && !matches.isEmpty()) {
                        String quoted = JSONObject.quote(matches.get(0));
                        runOnUiThread(() -> webView.evaluateJavascript("window.NexoraVoice && window.NexoraVoice.onResult(" + quoted + ")", null));
                    } else {
                        sendVoiceError("Tidak ada transkrip yang dapat digunakan.");
                    }
                }
                @Override public void onPartialResults(Bundle partialResults) {}
                @Override public void onEvent(int eventType, Bundle params) {}
            });
            Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "id-ID");
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, "id-ID");
            intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1);
            intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, false);
            speechRecognizer.startListening(intent);
        } catch (Exception error) {
            sendVoiceError("Tidak dapat memulai mikrofon: " + error.getMessage());
        }
    }

    private void sendVoiceError(String message) {
        String quoted = JSONObject.quote(message);
        runOnUiThread(() -> {
            if (webView != null) webView.evaluateJavascript("window.NexoraVoice && window.NexoraVoice.onError(" + quoted + ")", null);
        });
    }

    @Override public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == REQUEST_RECORD_AUDIO) {
            boolean granted = grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED;
            if (granted && speechStartPending) startSpeechRecognition();
            else sendVoiceError("Izin mikrofon diperlukan untuk input suara.");
            speechStartPending = false;
        }
    }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != 701 || fileCallback == null) return;
        Uri[] selected = null;
        if (resultCode == RESULT_OK && data != null) {
            if (data.getClipData() != null) {
                int count = data.getClipData().getItemCount(); selected = new Uri[count];
                for (int i = 0; i < count; i++) selected[i] = data.getClipData().getItemAt(i).getUri();
            } else if (data.getData() != null) selected = new Uri[]{data.getData()};
        }
        fileCallback.onReceiveValue(selected); fileCallback = null;
    }

    @Override public void onBackPressed() {
        if (webView != null && webView.canGoBack()) webView.goBack(); else super.onBackPressed();
    }

    private int dp(int value) { return (int) (value * getResources().getDisplayMetrics().density + 0.5f); }

    @Override protected void onDestroy() {
        if (fileCallback != null) { fileCallback.onReceiveValue(null); fileCallback = null; }
        if (speechRecognizer != null) { speechRecognizer.cancel(); speechRecognizer.destroy(); speechRecognizer = null; }
        if (webView != null) { webView.stopLoading(); webView.removeJavascriptInterface("NexoraNative"); webView.destroy(); webView = null; }
        super.onDestroy();
    }
}
