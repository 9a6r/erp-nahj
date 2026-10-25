import { createContext, useContext, useEffect } from "react"

const ThemeContext = createContext({ theme: "Dark" as const, themeValue: "Dark" as const })

/** Nahj intentionally has one consistent blue palette, independent of the OS theme. */
export function ThemeProvider({ children }: { children: React.ReactNode, defaultTheme?: string }) {
    useEffect(() => {
        const root = document.documentElement
        root.classList.remove('light')
        root.classList.add('dark', 'nahj-blue')
        return () => { root.classList.remove('nahj-blue') }
    }, [])
    return <ThemeContext.Provider value={{ theme: 'Dark', themeValue: 'Dark' }}>{children}</ThemeContext.Provider>
}
export const useTheme = () => useContext(ThemeContext)
