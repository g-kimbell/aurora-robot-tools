package main

import (
	"log"
	"os"
	"os/exec"
)

func main() {
	// When AutoSuite works correctly, we can pass in the arguements here. For now they have to be hardcoded.
	cmd := exec.Command("py", append([]string{"capacity_balance.py"}, "1")...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	err := cmd.Run()

	if err != nil {
		log.Fatalf("cmd.Run() failed with %s\n", err)
	}

	os.Exit(cmd.ProcessState.ExitCode())
}
