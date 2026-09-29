package com.apm.gibmobile.api

import android.content.Context
import android.net.Uri
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.util.UUID
import org.json.JSONObject

class ApiException(message: String, val code: String? = null) : Exception(message)

data class RunCreate(val runId: String, val status: String)
data class RunStatus(
    val runId: String,
    val status: String,
    val progress: Int,
    val recordsRetrieved: Int,
    val recordsNormalized: Int,
    val recordsClassified: Int,
    val normalizationErrors: Int,
    val previousBaselineAvailable: Boolean,
    val reportId: String?,
    val errorCode: String?
)
data class ReportSummary(
    val reportId: String,
    val runId: String,
    val status: String,
    val createdAt: String,
    val activityLevel: String?,
    val assessmentConfidence: String?,
    val recordsRetrieved: Int,
    val newCompromises: Int,
    val pdfAvailable: Boolean
)

class ApiClient(private val context: Context) {
    private val prefs = context.getSharedPreferences("gib_mobile", Context.MODE_PRIVATE)

    fun getBaseUrl(): String = prefs.getString("backend_url", "")?.trim()?.trimEnd('/') ?: ""

    fun setBaseUrl(value: String) {
        prefs.edit().putString("backend_url", value.trim().trimEnd('/')).apply()
    }

    fun startRun(): RunCreate {
        val key = UUID.randomUUID().toString()
        val json = request("POST", "/api/v1/runs", mapOf("Idempotency-Key" to key))
        return RunCreate(json.getString("run_id"), json.getString("status"))
    }

    fun getRun(runId: String): RunStatus {
        val json = request("GET", "/api/v1/runs/${Uri.encode(runId)}")
        return RunStatus(
            runId = json.getString("run_id"),
            status = json.getString("status"),
            progress = json.getInt("progress"),
            recordsRetrieved = json.getInt("records_retrieved"),
            recordsNormalized = json.getInt("records_normalized"),
            recordsClassified = json.getInt("records_classified"),
            normalizationErrors = json.getInt("normalization_errors"),
            previousBaselineAvailable = json.getBoolean("previous_baseline_available"),
            reportId = json.optString("report_id").takeIf { it.isNotBlank() && it != "null" },
            errorCode = json.optString("error_code").takeIf { it.isNotBlank() && it != "null" }
        )
    }

    fun getLatestReport(): ReportSummary = parseReport(request("GET", "/api/v1/reports/latest"))

    fun getHistory(): List<ReportSummary> {
        val items = request("GET", "/api/v1/reports/history?limit=50&offset=0").getJSONArray("items")
        return (0 until items.length()).map { parseReport(items.getJSONObject(it)) }
    }

    fun downloadReport(reportId: String): File {
        val directory = File(context.cacheDir, "reports").apply { mkdirs() }
        val file = File(directory, "$reportId.pdf")
        val connection = open("GET", "/api/v1/reports/${Uri.encode(reportId)}/download")
        try {
            checkResponse(connection)
            connection.inputStream.use { input ->
                file.outputStream().use { output -> input.copyTo(output) }
            }
        } finally {
            connection.disconnect()
        }
        return file
    }

    private fun parseReport(json: JSONObject) = ReportSummary(
        reportId = json.getString("report_id"),
        runId = json.getString("run_id"),
        status = json.getString("status"),
        createdAt = json.getString("created_at"),
        activityLevel = json.optString("activity_level").takeIf { it.isNotBlank() && it != "null" },
        assessmentConfidence = json.optString("assessment_confidence").takeIf { it.isNotBlank() && it != "null" },
        recordsRetrieved = json.getInt("records_retrieved"),
        newCompromises = json.getInt("new_compromises"),
        pdfAvailable = json.getBoolean("pdf_available")
    )

    private fun request(method: String, path: String, headers: Map<String, String> = emptyMap()): JSONObject {
        val connection = open(method, path)
        try {
            headers.forEach { (key, value) -> connection.setRequestProperty(key, value) }
            checkResponse(connection)
            val body = connection.inputStream.bufferedReader().use { it.readText() }
            return JSONObject(body)
        } finally {
            connection.disconnect()
        }
    }

    private fun open(method: String, path: String): HttpURLConnection {
        val base = getBaseUrl()
        require(base.isNotBlank()) { "Backend URL is not configured." }
        val connection = (URL("$base$path").openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 15_000
            readTimeout = 30_000
            useCaches = false
            doInput = true
            setRequestProperty("Accept", "application/json")
        }
        return connection
    }

    private fun checkResponse(connection: HttpURLConnection) {
        if (connection.responseCode in 200..299) return
        val body = runCatching {
            connection.errorStream?.bufferedReader()?.use { it.readText() }
        }.getOrNull().orEmpty()
        val error = runCatching { JSONObject(body).getJSONObject("error") }.getOrNull()
        throw ApiException(
            message = error?.optString("message").takeUnless { it.isNullOrBlank() }
                ?: "Backend request failed (${connection.responseCode}).",
            code = error?.optString("code")
        )
    }
}