package com.apm.gibmobile

import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import androidx.lifecycle.viewmodel.compose.viewModel
import java.io.File

@OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)
@Composable
fun GibMobileApp(viewModel: GibViewModel = viewModel()) {
    val state by viewModel.state
    var tab by remember { mutableIntStateOf(0) }

    Scaffold(topBar = { TopAppBar(title = { Text("GIB Threat Reporter") }) }) { padding ->
        Column(
            modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = { tab = 0 }) { Text("Dashboard") }
                OutlinedButton(onClick = { tab = 1; viewModel.loadHistory() }) { Text("History") }
                OutlinedButton(onClick = { tab = 2 }) { Text("Settings") }
            }
            when (tab) {
                0 -> Dashboard(state, viewModel)
                1 -> History(state, viewModel)
                else -> Settings(state, viewModel)
            }
        }
    }
}

@Composable
private fun Dashboard(state: GibUiState, viewModel: GibViewModel) {
    Text("Group-IB Mobile Threat Intelligence Reporter", style = MaterialTheme.typography.headlineSmall)
    StatusCard(state)
    Button(
        onClick = viewModel::generateReport,
        enabled = !state.running && state.backendUrl.isNotBlank(),
        modifier = Modifier.fillMaxWidth().height(56.dp)
    ) {
        Text(if (state.running) "GENERATING REPORT…" else "GENERATE GIB REPORT")
    }
    if (state.running) LinearProgressIndicator(progress = { state.progress / 100f }, modifier = Modifier.fillMaxWidth())
    state.message?.let { Text(it, color = MaterialTheme.colorScheme.primary) }
    state.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
    state.pdfFile?.let { ReportActions(it) }
}

@Composable
private fun StatusCard(state: GibUiState) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text("Backend", style = MaterialTheme.typography.titleMedium)
            Text(if (state.backendUrl.isBlank()) "Not configured" else state.backendUrl)
            Text("Status: ${state.status}")
            Text("Progress: ${state.progress}%")
            state.latestReport?.let {
                Text("NEW compromises: ${it.newCompromises}")
                Text("Activity: ${it.activityLevel ?: "N/A"}")
                Text("Confidence: ${it.assessmentConfidence ?: "N/A"}")
            }
        }
    }
}

@Composable
private fun History(state: GibUiState, viewModel: GibViewModel) {
    if (state.history.isEmpty()) { Text("No successful reports found."); return }
    LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        items(state.history, key = { it.reportId }) { report ->
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text(report.createdAt, style = MaterialTheme.typography.titleMedium)
                    Text("Activity: ${report.activityLevel ?: "N/A"}")
                    Text("NEW compromises: ${report.newCompromises}")
                    if (report.pdfAvailable) Button(onClick = { viewModel.downloadReport(report.reportId) }) { Text("DOWNLOAD PDF") }
                }
            }
        }
    }
}

@Composable
private fun Settings(state: GibUiState, viewModel: GibViewModel) {
    var url by remember(state.backendUrl) { mutableStateOf(state.backendUrl) }
    Text("Backend Settings", style = MaterialTheme.typography.headlineSmall)
    OutlinedTextField(
        value = url,
        onValueChange = { url = it },
        modifier = Modifier.fillMaxWidth(),
        label = { Text("HTTPS backend URL") },
        supportingText = { Text("Example: https://backend.example.com") },
        singleLine = true
    )
    Spacer(Modifier.height(8.dp))
    Button(onClick = { viewModel.setBackendUrl(url) }) { Text("SAVE BACKEND URL") }
}

@Composable
private fun ReportActions(file: File) {
    val context = LocalContext.current
    val saveLauncher = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/pdf")) { uri ->
        if (uri != null) savePdf(context, uri, file)
    }
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Button(onClick = { openPdf(context, file) }) { Text("VIEW REPORT") }
        OutlinedButton(onClick = { sharePdf(context, file) }) { Text("SHARE PDF") }
        OutlinedButton(onClick = { saveLauncher.launch(file.name) }) { Text("SAVE PDF") }
    }
}

private fun openPdf(context: Context, file: File) {
    val uri = FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", file)
    context.startActivity(Intent(Intent.ACTION_VIEW).apply {
        setDataAndType(uri, "application/pdf")
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    })
}

private fun sharePdf(context: Context, file: File) {
    val uri = FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", file)
    context.startActivity(Intent.createChooser(Intent(Intent.ACTION_SEND).apply {
        type = "application/pdf"
        putExtra(Intent.EXTRA_STREAM, uri)
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    }, "Share GIB report"))
}

private fun savePdf(context: Context, uri: Uri, file: File) {
    context.contentResolver.openOutputStream(uri)?.use { output ->
        file.inputStream().use { input -> input.copyTo(output) }
    }
}