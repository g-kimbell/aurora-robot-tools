package main

import (
	"log"
	"os"
	"os/exec"
)

func main() {
	cmd := exec.Command("py", []string{"assign_cells_to_press.py"}...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	err := cmd.Run()

	if err != nil {
		log.Fatalf("cmd.Run() failed with %s\n", err)
	}

	os.Exit(cmd.ProcessState.ExitCode())
}
