import SwiftUI

struct MainTabView: View {
    @State private var selectedTab = 0

    init() {
        let appearance = UITabBarAppearance()
        appearance.configureWithOpaqueBackground()
        appearance.backgroundColor = .white

        appearance.stackedLayoutAppearance.normal.iconColor = UIColor(.textSecondary)
        appearance.stackedLayoutAppearance.normal.titleTextAttributes = [.foregroundColor:UIColor(.textSecondary)]

        appearance.stackedLayoutAppearance.selected.iconColor = UIColor(.primaryWine)
        appearance.stackedLayoutAppearance.selected.titleTextAttributes = [.foregroundColor: UIColor(.primaryWine)]

        UITabBar.appearance().standardAppearance = appearance
        UITabBar.appearance().scrollEdgeAppearance = appearance
    }

    var body: some View {
        TabView(selection: $selectedTab) {
            HomeView()
                .tabItem {
                    Image(systemName: selectedTab == 0 ? "house.fill" : "house")
                    Text("Главная")
                }
                .tag(0)

            ProfileView()
                .tabItem {
                    Image(systemName: selectedTab == 1 ? "person.fill" : "person")
                    Text("Профиль")
                }
                .tag(1)

        }
        .accentColor(.primaryWine)
    }
}

