const TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify";

const MAX_FIELD_LENGTHS = {
  name: 120,
  email: 254,
  msgsubject: 180,
  message: 4000,
  vocab: 80,
};

function jsonResponse(body, status = 200, headers = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      ...headers,
    },
  });
}

function normalizeString(value, maxLength) {
  return String(value || "").trim().slice(0, maxLength);
}

function parseFeedbackForm(formData) {
  return {
    vocab: normalizeString(formData.get("vocab"), MAX_FIELD_LENGTHS.vocab),
    name: normalizeString(formData.get("name"), MAX_FIELD_LENGTHS.name),
    email: normalizeString(formData.get("email"), MAX_FIELD_LENGTHS.email),
    subject: normalizeString(formData.get("msgsubject"), MAX_FIELD_LENGTHS.msgsubject),
    message: normalizeString(formData.get("message"), MAX_FIELD_LENGTHS.message),
    honeypot: normalizeString(formData.get("item-description"), 200),
    turnstileToken: normalizeString(formData.get("cf-turnstile-response"), 2048),
  };
}

function isValidEmail(email) {
  return email === "" || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function validateOrigin(request, env) {
  const allowedOrigin = env.ALLOWED_ORIGIN || "https://soilvoc.wangbeichen.com";
  const origin = request.headers.get("origin");
  return !origin || origin === allowedOrigin;
}

function buildEmailMessage(feedback, request, env) {
  const remoteIp = request.headers.get("cf-connecting-ip") || "unknown";
  const userAgent = request.headers.get("user-agent") || "unknown";
  const referer = request.headers.get("referer") || "unknown";
  const name = feedback.name || "anonymous user";
  const text = [
    `Vocabulary: ${feedback.vocab || "not specified"}`,
    `Name: ${name}`,
    `Email: ${feedback.email || "not provided"}`,
    "",
    feedback.message,
    "",
    "Debugging information:",
    `Timestamp: ${new Date().toISOString()}`,
    `IP: ${remoteIp}`,
    `User agent: ${userAgent}`,
    `Referer: ${referer}`,
  ].join("\n");

  const message = {
    to: env.FEEDBACK_TO,
    from: { email: env.FEEDBACK_FROM, name: "SoilVoc feedback" },
    subject: `[SoilVoc feedback] ${feedback.subject}`,
    text,
  };

  if (feedback.email) {
    message.replyTo = { email: feedback.email, name };
  }

  return message;
}

async function defaultVerifyTurnstile(token, secret, remoteIp) {
  const formData = new FormData();
  formData.append("secret", secret);
  formData.append("response", token);
  if (remoteIp) {
    formData.append("remoteip", remoteIp);
  }
  formData.append("idempotency_key", crypto.randomUUID());

  const response = await fetch(TURNSTILE_VERIFY_URL, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    return { success: false, "error-codes": [`siteverify-http-${response.status}`] };
  }

  return response.json();
}

async function handleFeedback(request, env, verifyTurnstile) {
  if (!validateOrigin(request, env)) {
    return jsonResponse({ ok: false, error: "Feedback can only be submitted from SoilVoc." }, 403);
  }

  if (!env.FEEDBACK_TO || !env.FEEDBACK_FROM || !env.EMAIL) {
    console.error("Feedback Worker is missing FEEDBACK_TO, FEEDBACK_FROM, or EMAIL binding.");
    return jsonResponse({ ok: false, error: "Feedback is not configured yet." }, 503);
  }

  const contentType = request.headers.get("content-type") || "";
  if (!contentType.includes("application/x-www-form-urlencoded") && !contentType.includes("multipart/form-data")) {
    return jsonResponse({ ok: false, error: "Unsupported form encoding." }, 415);
  }

  const feedback = parseFeedbackForm(await request.formData());
  if (feedback.honeypot) {
    return jsonResponse({ ok: true });
  }
  if (!feedback.subject) {
    return jsonResponse({ ok: false, error: "Subject is required." }, 400);
  }
  if (!feedback.message) {
    return jsonResponse({ ok: false, error: "Message is required." }, 400);
  }
  if (!isValidEmail(feedback.email)) {
    return jsonResponse({ ok: false, error: "Please enter a valid email address or leave it empty." }, 400);
  }

  if (env.TURNSTILE_SECRET) {
    if (!feedback.turnstileToken) {
      return jsonResponse({ ok: false, error: "Verification is required. Please try again." }, 400);
    }
    const remoteIp = request.headers.get("cf-connecting-ip") || "";
    const validation = await verifyTurnstile(feedback.turnstileToken, env.TURNSTILE_SECRET, remoteIp);
    if (!validation.success) {
      console.warn("Turnstile validation failed", validation["error-codes"] || []);
      return jsonResponse({ ok: false, error: "Verification failed. Please try again." }, 400);
    }
  }

  try {
    const result = await env.EMAIL.send(buildEmailMessage(feedback, request, env));
    return jsonResponse({ ok: true, messageId: result.messageId || null });
  } catch (error) {
    console.error("Feedback email failed", error?.code || "", error?.message || error);
    const body = { ok: false, error: "Could not send feedback right now. Please try again later." };
    if (env.DEBUG_ERRORS === "true" && error?.code) {
      body.errorCode = error.code;
    }
    return jsonResponse(body, 502);
  }
}

export function createFeedbackWorker(options = {}) {
  const verifyTurnstile = options.verifyTurnstile || defaultVerifyTurnstile;

  return {
    async fetch(request, env) {
      if (request.method === "GET" || request.method === "HEAD") {
        return new Response("SoilVoc feedback endpoint\n", {
          headers: { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" },
        });
      }

      if (request.method !== "POST") {
        return jsonResponse({ ok: false, error: "Method not allowed." }, 405, { allow: "GET, POST" });
      }

      return handleFeedback(request, env, verifyTurnstile);
    },
  };
}

export default createFeedbackWorker();
