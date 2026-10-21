package app.asksiddha.mobile;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import com.google.android.play.core.review.ReviewInfo;
import com.google.android.play.core.review.ReviewManager;
import com.google.android.play.core.review.ReviewManagerFactory;

/**
 * Google Play's in-app rating card (audit N23).
 *
 * Play decides whether the card actually shows (it is rationed per reader,
 * and never shows on internal or closed testing builds installed outside
 * the Play listing), and never says whether the reader rated. So request()
 * resolves { asked: true } once the flow has run, and { asked: false } when
 * Play could not start it; neither is an error the reader should see.
 * When to ask is decided in the web layer (core/rating-prompt.ts).
 */
@CapacitorPlugin(name = "InAppReview")
public class InAppReviewPlugin extends Plugin {

    @PluginMethod
    public void request(PluginCall call) {
        ReviewManager manager = ReviewManagerFactory.create(getContext());
        manager.requestReviewFlow().addOnCompleteListener(request -> {
            if (!request.isSuccessful() || getActivity() == null) {
                resolve(call, false);
                return;
            }
            ReviewInfo info = request.getResult();
            manager.launchReviewFlow(getActivity(), info).addOnCompleteListener(flow -> resolve(call, true));
        });
    }

    private static void resolve(PluginCall call, boolean asked) {
        JSObject result = new JSObject();
        result.put("asked", asked);
        call.resolve(result);
    }
}
