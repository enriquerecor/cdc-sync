import {
  ActionIcon,
  Tooltip,
  useComputedColorScheme,
  useMantineColorScheme,
} from "@mantine/core";
import { Moon, Sun } from "lucide-react";

export function ColorSchemeToggle() {
  const { toggleColorScheme } = useMantineColorScheme();
  const computedColorScheme = useComputedColorScheme("light", {
    getInitialValueInEffect: false,
  });
  const isDark = computedColorScheme === "dark";
  const label = isDark ? "Cambiar a tema claro" : "Cambiar a tema oscuro";

  return (
    <Tooltip label={label}>
      <ActionIcon
        aria-label={label}
        className="color-scheme-toggle"
        variant="transparent"
        onClick={toggleColorScheme}
      >
        {isDark ? (
          <Sun size={18} strokeWidth={1.8} />
        ) : (
          <Moon size={18} strokeWidth={1.8} />
        )}
      </ActionIcon>
    </Tooltip>
  );
}
