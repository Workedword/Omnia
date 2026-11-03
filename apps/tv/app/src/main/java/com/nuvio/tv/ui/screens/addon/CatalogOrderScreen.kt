@file:OptIn(ExperimentalTvMaterial3Api::class)

package com.nuvio.tv.ui.screens.addon

import com.nuvio.tv.ui.theme.NuvioTheme

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowDownward
import androidx.compose.material.icons.filled.ArrowUpward
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.runtime.getValue
import android.view.KeyEvent
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.runtime.remember
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.input.key.onPreviewKeyEvent
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.runtime.withFrameNanos
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.tv.material3.Border
import androidx.tv.material3.Button
import androidx.tv.material3.ButtonDefaults
import androidx.tv.material3.ExperimentalTvMaterial3Api
import androidx.tv.material3.Icon
import androidx.tv.material3.MaterialTheme
import androidx.tv.material3.Text
import com.nuvio.tv.ui.components.LoadingIndicator
import androidx.compose.ui.res.stringResource
import com.nuvio.tv.R
import kotlinx.coroutines.launch

@Composable
fun CatalogOrderScreen(
    viewModel: CatalogOrderViewModel = hiltViewModel(),
    onBackPress: () -> Unit
) {
    val uiState by viewModel.uiState.collectAsState()
    val listState = rememberLazyListState()
    val scope = rememberCoroutineScope()
    val catalogControlsFocus = remember { FocusRequester() }
    val catalogSearchFieldFocus = remember { FocusRequester() }
    var catalogSearchEditing by rememberSaveable { mutableStateOf(false) }
    val keyboardController = LocalSoftwareKeyboardController.current
    var catalogQuery by rememberSaveable { mutableStateOf("") }
    var catalogVisibility by rememberSaveable { mutableStateOf("All") }
    val visibleCatalogs = filterHomeCatalogs(uiState.items, catalogQuery, catalogVisibility)
    val filtering = catalogQuery.isNotBlank() || catalogVisibility != "All"

    // Omnia deliberate catalog search. Catalog controls are usable before opening the keyboard.
    LaunchedEffect(Unit) {
        repeat(2) { withFrameNanos { } }
        keyboardController?.hide()
        catalogControlsFocus.requestFocus()
    }
    LaunchedEffect(catalogSearchEditing) {
        if (catalogSearchEditing) {
            repeat(2) { withFrameNanos { } }
            catalogSearchFieldFocus.requestFocus()
            keyboardController?.show()
        }
    }
    BackHandler {
        if (catalogSearchEditing) {
            catalogSearchEditing = false
            keyboardController?.hide()
            catalogControlsFocus.requestFocus()
        } else onBackPress()
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = NuvioTheme.spacing.xxxl, vertical = NuvioTheme.spacing.xl)
    ) {
        LazyColumn(
            state = listState,
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(bottom = NuvioTheme.spacing.xl),
            verticalArrangement = Arrangement.spacedBy(NuvioTheme.spacing.lg)
        ) {
            item {
                Text(
                    text = stringResource(R.string.catalog_order_title),
                    style = MaterialTheme.typography.headlineLarge,
                    color = NuvioTheme.colors.TextPrimary
                )
                Spacer(modifier = Modifier.height(NuvioTheme.spacing.sm))
                Text(
                    text = stringResource(R.string.catalog_order_subtitle),
                    style = MaterialTheme.typography.bodyMedium,
                    color = NuvioTheme.colors.TextSecondary
                )
                Spacer(modifier = Modifier.height(NuvioTheme.spacing.lg))
                val followAddonsLabel = stringResource(R.string.catalog_order_follow_addons)
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = followAddonsLabel,
                            style = MaterialTheme.typography.titleMedium,
                            color = NuvioTheme.colors.TextPrimary
                        )
                        Text(
                            text = stringResource(R.string.catalog_order_follow_addons_desc),
                            style = MaterialTheme.typography.bodySmall,
                            color = NuvioTheme.colors.TextSecondary
                        )
                    }
                    Switch(
                        checked = uiState.followAddonsOrder,
                        onCheckedChange = { viewModel.toggleFollowAddonsOrder(it) },
                        modifier = Modifier.semantics { contentDescription = followAddonsLabel },
                        colors = SwitchDefaults.colors(
                            checkedThumbColor = NuvioTheme.colors.Primary,
                            checkedTrackColor = NuvioTheme.colors.Primary.copy(alpha = 0.5f)
                        )
                    )
                }
            }

            item(key = "catalog_filters") {
                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    if (catalogSearchEditing) {
                        OutlinedTextField(
                            value = catalogQuery,
                            onValueChange = { catalogQuery = it },
                            label = { Text("Search catalogs or providers") },
                            singleLine = true,
                            keyboardOptions = KeyboardOptions.Default.copy(imeAction = ImeAction.Done),
                            keyboardActions = KeyboardActions(onDone = {
                                catalogSearchEditing = false
                                keyboardController?.hide()
                                catalogControlsFocus.requestFocus()
                            }),
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedTextColor = NuvioTheme.colors.TextPrimary,
                                unfocusedTextColor = NuvioTheme.colors.TextPrimary,
                                cursorColor = NuvioTheme.colors.Primary,
                                focusedBorderColor = NuvioTheme.colors.Primary,
                                unfocusedBorderColor = NuvioTheme.colors.TextSecondary
                            ),
                            modifier = Modifier.fillMaxWidth().focusRequester(catalogSearchFieldFocus).onPreviewKeyEvent { event ->
                                if (event.nativeKeyEvent.keyCode == KeyEvent.KEYCODE_DPAD_DOWN) {
                                    if (event.nativeKeyEvent.action == KeyEvent.ACTION_DOWN) {
                                        catalogSearchEditing = false
                                        keyboardController?.hide()
                                        catalogControlsFocus.requestFocus()
                                    }
                                    true
                                } else false
                            }
                        )
                    } else {
                        Button(
                            onClick = { catalogSearchEditing = true },
                            modifier = Modifier.fillMaxWidth(),
                            colors = ButtonDefaults.colors(
                                containerColor = NuvioTheme.colors.BackgroundCard,
                                contentColor = NuvioTheme.colors.TextPrimary,
                                focusedContainerColor = NuvioTheme.colors.FocusBackground,
                                focusedContentColor = NuvioTheme.colors.Primary
                            )
                        ) {
                            Column(modifier = Modifier.fillMaxWidth()) {
                                Text("Search catalogs or providers")
                                if (catalogQuery.isNotBlank()) Text(catalogQuery, style = MaterialTheme.typography.bodySmall)
                            }
                        }
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        listOf("All", "Shown", "Hidden").forEach { filter ->
                            Button(
                                onClick = { catalogVisibility = filter },
                                modifier = if (filter == "All") Modifier.focusRequester(catalogControlsFocus) else Modifier
                            ) {
                                Text(if (catalogVisibility == filter) "✓ $filter" else filter)
                            }
                        }
                        if (filtering) {
                            Button(onClick = {
                                catalogControlsFocus.requestFocus()
                                keyboardController?.hide()
                                catalogQuery = ""
                                catalogVisibility = "All"
                            }) { Text("Clear filters") }
                        }
                    }
                    Text("${visibleCatalogs.size} of ${uiState.items.size} catalogs • Choose which rows appear on Home",
                        color = NuvioTheme.colors.TextSecondary)
                    if (filtering) Text("Clear filters to reorder catalogs.", color = NuvioTheme.colors.TextSecondary)
                }
            }
            when {
                uiState.isLoading -> {
                    item {
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = NuvioTheme.spacing.xl),
                            contentAlignment = Alignment.Center
                        ) {
                            LoadingIndicator()
                        }
                    }
                }

                visibleCatalogs.isEmpty() -> {
                    item {
                        Text(
                            text = if (uiState.items.isEmpty()) stringResource(R.string.catalog_order_empty) else "No catalogs match these filters.",
                            style = MaterialTheme.typography.bodyLarge,
                            color = NuvioTheme.colors.TextSecondary
                        )
                    }
                }

                else -> {
                    itemsIndexed(
                        items = visibleCatalogs,
                        key = { _, item -> item.key }
                    ) { index, item ->
                        CatalogOrderCard(
                            item = if (filtering) item.copy(canMoveUp = false, canMoveDown = false) else item,
                            onMoveUp = {
                                viewModel.moveUp(item.key)
                                scope.launch {
                                    listState.animateScrollToItem((index + 1).coerceAtLeast(2))
                                }
                            },
                            onMoveDown = {
                                viewModel.moveDown(item.key)
                                scope.launch {
                                    listState.animateScrollToItem(
                                        (index + 3).coerceAtMost(visibleCatalogs.lastIndex + 2)
                                    )
                                }
                            },
                            onToggleEnabled = {
                                if (catalogVisibility == "All") {
                                    viewModel.toggleCatalogEnabled(item.disableKey)
                                } else {
                                    // The toggled row leaves a visibility-filtered list. Move focus
                                    // before removing it so focus restoration cannot reopen Search's IME.
                                    scope.launch {
                                        listState.scrollToItem(1)
                                        withFrameNanos { }
                                        catalogControlsFocus.requestFocus()
                                        keyboardController?.hide()
                                        viewModel.toggleCatalogEnabled(item.disableKey)
                                    }
                                }
                            }
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun CatalogOrderCard(
    item: CatalogOrderItem,
    onMoveUp: () -> Unit,
    onMoveDown: () -> Unit,
    onToggleEnabled: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = NuvioTheme.colors.BackgroundCard),
        shape = RoundedCornerShape(NuvioTheme.radii.md)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(20.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "${item.catalogName} - ${item.typeLabel.toDisplayTypeLabel()}",
                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                    color = if (item.isDisabled) NuvioTheme.colors.TextSecondary else NuvioTheme.colors.TextPrimary
                )
                Spacer(modifier = Modifier.height(NuvioTheme.spacing.xs))
                Text(
                    text = item.addonName,
                    style = MaterialTheme.typography.bodySmall,
                    color = NuvioTheme.colors.TextSecondary
                )
                if (item.isDisabled) {
                    Spacer(modifier = Modifier.height(NuvioTheme.spacing.xs))
                    Text(
                        text = stringResource(R.string.catalog_order_disabled_on_home),
                        style = MaterialTheme.typography.bodySmall,
                        color = NuvioTheme.colors.Error
                    )
                }
            }

            Row(
                horizontalArrangement = Arrangement.spacedBy(NuvioTheme.spacing.sm),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Button(
                    onClick = onMoveUp,
                    enabled = item.canMoveUp,
                    colors = ButtonDefaults.colors(
                        containerColor = NuvioTheme.colors.BackgroundCard,
                        contentColor = NuvioTheme.colors.TextSecondary,
                        focusedContainerColor = NuvioTheme.colors.FocusBackground,
                        focusedContentColor = NuvioTheme.colors.Primary
                    ),
                    border = ButtonDefaults.border(
                        focusedBorder = Border(
                            border = NuvioTheme.focusRing.border(NuvioTheme.spacing.xxs),
                            shape = RoundedCornerShape(NuvioTheme.radii.md)
                        )
                    ),
                    shape = ButtonDefaults.shape(RoundedCornerShape(NuvioTheme.radii.md))
                ) {
                    Icon(
                        imageVector = Icons.Default.ArrowUpward,
                        contentDescription = stringResource(R.string.cd_move_up)
                    )
                }

                Button(
                    onClick = onMoveDown,
                    enabled = item.canMoveDown,
                    colors = ButtonDefaults.colors(
                        containerColor = NuvioTheme.colors.BackgroundCard,
                        contentColor = NuvioTheme.colors.TextSecondary,
                        focusedContainerColor = NuvioTheme.colors.FocusBackground,
                        focusedContentColor = NuvioTheme.colors.Primary
                    ),
                    border = ButtonDefaults.border(
                        focusedBorder = Border(
                            border = NuvioTheme.focusRing.border(NuvioTheme.spacing.xxs),
                            shape = RoundedCornerShape(NuvioTheme.radii.md)
                        )
                    ),
                    shape = ButtonDefaults.shape(RoundedCornerShape(NuvioTheme.radii.md))
                ) {
                    Icon(
                        imageVector = Icons.Default.ArrowDownward,
                        contentDescription = stringResource(R.string.cd_move_down)
                    )
                }

                Button(
                    onClick = onToggleEnabled,
                    colors = ButtonDefaults.colors(
                        containerColor = NuvioTheme.colors.BackgroundCard,
                        contentColor = if (item.isDisabled) NuvioTheme.colors.Success else NuvioTheme.colors.TextSecondary,
                        focusedContainerColor = NuvioTheme.colors.FocusBackground,
                        focusedContentColor = if (item.isDisabled) NuvioTheme.colors.Success else NuvioTheme.colors.Error
                    ),
                    border = ButtonDefaults.border(
                        focusedBorder = Border(
                            border = NuvioTheme.focusRing.border(NuvioTheme.spacing.xxs),
                            shape = RoundedCornerShape(NuvioTheme.radii.md)
                        )
                    ),
                    shape = ButtonDefaults.shape(RoundedCornerShape(NuvioTheme.radii.md))
                ) {
                    Text(text = if (item.isDisabled) stringResource(R.string.catalog_order_enable) else stringResource(R.string.catalog_order_disable))
                }
            }
        }
    }
}

private fun String.toDisplayTypeLabel(): String {
    return replaceFirstChar { ch ->
        if (ch.isLowerCase()) ch.titlecase() else ch.toString()
    }
}

internal fun filterHomeCatalogs(items: List<CatalogOrderItem>, query: String, visibility: String): List<CatalogOrderItem> =
    items.filter { catalog ->
        val term = query.trim()
        (term.isEmpty() || catalog.catalogName.contains(term, ignoreCase = true) ||
            catalog.addonName.contains(term, ignoreCase = true)) &&
            (visibility == "All" || (visibility == "Shown" && !catalog.isDisabled) ||
                (visibility == "Hidden" && catalog.isDisabled))
    }
