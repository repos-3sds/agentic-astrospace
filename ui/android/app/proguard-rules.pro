# Add project specific ProGuard rules here.
# You can control the set of applied configuration files using the
# proguardFiles setting in build.gradle.
#
# For more details, see
#   http://developer.android.com/guide/developing/tools/proguard.html

# If your project uses WebView with JS, uncomment the following
# and specify the fully qualified class name to the JavaScript interface
# class:
#-keepclassmembers class fqcn.of.javascript.interface.for.webview {
#   public *;
#}

# Uncomment this to preserve the line number information for
# debugging stack traces.
#-keepattributes SourceFile,LineNumberTable

# If you keep the line number information, uncomment this to
# hide the original source file name.
#-renamesourcefileattribute SourceFile

# Capacitor finds plugins by annotation and calls @PluginMethod handlers by
# name over the bridge; a renamed method is a silent "method not implemented".
# @capacitor/android carries consumer rules for its own classes and the
# official plugins. The community plugins below do not all ship theirs, so
# they are kept here. Readable stack traces are worth the few KB.
-keepattributes SourceFile,LineNumberTable
-keep @com.getcapacitor.annotation.CapacitorPlugin public class * {
    @com.getcapacitor.PluginMethod public <methods>;
}
-keep public class * extends com.getcapacitor.Plugin
-keep class com.getcapacitor.community.** { *; }
-keep class net.sqlcipher.** { *; }
-keep class net.zetetic.** { *; }
-keep class com.whitestein.securestorage.** { *; }
