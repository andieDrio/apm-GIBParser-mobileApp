package com.apm.gibmobile

import android.app.Application
import android.os.Handler
import android.os.Looper
import androidx.compose.runtime.mutableStateOf
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.apm.gibmobile.api.ApiClient
import com.apm.gibmobile.api.ReportSummary
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.io.File

data class GibUiState(
    val backendUrl: String = "",
    val running: Boolean = false,
    val status: String = "NOT_CONFIGURED",
    val progress: Int = 0,
    val runId: String? = null,
    val reportId: String? = null,
    val latestReport: ReportSummary? = null,
    val history: List<ReportSummary> = emptyList(),
    val pdfFile: File? = null,
    val message: String? = null,
    val error: String? = null
)

class GibViewModel(application: Application) : AndroidViewModel(application) {
    private val api = ApiClient(application)
    private val mainHandler = Handler(Looper.getMainLooper())

    var state = mutableStateOf(GibUiState(backendUrl = api.getBaseUrl()))
        private set

    fun setBackendUrl(value: String) {
        api.setBaseUrl(value)
        state.value = state.value.copy(backendUrl = api.getBaseUrl(), error = null, message = "Backend URL saved.")
    }

    fun generateReport() {
        if (api.getBaseUrl().isBlank()) {
            state.value = state.value.copy(error = "Configure the backend URL first.")
            return
        }
        if (state.value.running) return
        state.value = state.value.copy(running = true, status = "STARTING", progress = 0, error = null, message = null)

        viewModelScope.launch(Dispatchers.IO) {
            try {
                val created = api.startRun()
                update { it.copy(runId = created.runId, status = created.status) }
                pollUntilTerminal(created.runId)
            } catch (e: Exception) {
                update { it.copy(running = false, error = e.message ?: "Unable to generate report.") }
            }
        }
    }

    private suspend fun pollUntilTerminal(runId: String) {
        repeat(180) {
            val run = api.getRun(runId)
            update {
                it.copy(
                    status = run.status,
                    progress = run.progress,
                    reportId = run.reportId,
                    running = run.status !in setOf("SUCCEEDED", "FAILED", "PARTIAL"),
                    error = if (run.status == "FAILED" || run.status == "PARTIAL") run.errorCode else null
                )
            }
            if (run.status == "SUCCEEDED") {
                val reportId = run.reportId ?: error("Successful run did not return a report ID.")
                val file = api.downloadReport(reportId)
                val latest = api.getLatestReport()
                update { it.copy(running = false, pdfFile = file, latestReport = latest, message = "Report generated successfully.") }
                return
            }
            if (run.status == "FAILED" || run.status == "PARTIAL") return
            delay(1000)
        }
        error("Report generation timed out while waiting for the backend.")
    }

    fun loadHistory() {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val history = api.getHistory()
                update { it.copy(history = history, error = null) }
            } catch (e: Exception) {
                update { it.copy(error = e.message ?: "Unable to load report history.") }
            }
        }
    }

    fun downloadReport(reportId: String) {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val file = api.downloadReport(reportId)
                update { it.copy(pdfFile = file, message = "Report ready.") }
            } catch (e: Exception) {
                update { it.copy(error = e.message ?: "Unable to download report.") }
            }
        }
    }

    private fun update(block: (GibUiState) -> GibUiState) {
        mainHandler.post { state.value = block(state.value) }
    }
}