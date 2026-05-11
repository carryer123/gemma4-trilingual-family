package com.moontech.trilingual.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.moontech.trilingual.llm.LlmBackend
import com.moontech.trilingual.ui.screens.*

private enum class Tab(val route: String, val label: String, val icon: ImageVector) {
    Card("card", "Card", Icons.Filled.PhotoCamera),
    Story("story", "Story", Icons.Filled.NightsStay),
    Daily("daily", "Daily", Icons.Filled.WbSunny),
    Family("family", "Family", Icons.Filled.Group),
    Game("game", "Game", Icons.Filled.RecordVoiceOver),
    Meal("meal", "Meal", Icons.Filled.Restaurant),
}

@Composable
fun TrilingualApp(llm: LlmBackend) {
    val nav = rememberNavController()
    val backStack by nav.currentBackStackEntryAsState()
    val currentRoute = backStack?.destination?.route

    Scaffold(
        bottomBar = {
            NavigationBar {
                Tab.entries.forEach { tab ->
                    NavigationBarItem(
                        selected = currentRoute == tab.route,
                        onClick = {
                            nav.navigate(tab.route) {
                                popUpTo(nav.graph.findStartDestination().id) { saveState = true }
                                launchSingleTop = true
                                restoreState = true
                            }
                        },
                        icon = { Icon(tab.icon, contentDescription = tab.label) },
                        label = { Text(tab.label) },
                    )
                }
            }
        }
    ) { padding ->
        NavHost(
            navController = nav,
            startDestination = Tab.Card.route,
            modifier = Modifier.padding(padding),
        ) {
            composable(Tab.Card.route)   { ObjectCardScreen(llm) }
            composable(Tab.Story.route)  { BedtimeStoryScreen(llm) }
            composable(Tab.Daily.route)  { DailyPhraseScreen(llm) }
            composable(Tab.Family.route) { FamilyWordScreen(llm) }
            composable(Tab.Game.route)   { PronunciationGameScreen(llm) }
            composable(Tab.Meal.route)   { MealtimeScreen(llm) }
        }
    }
}
