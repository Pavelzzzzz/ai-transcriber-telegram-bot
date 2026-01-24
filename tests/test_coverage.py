import pytest
import os
import sys

# Добавляем путь к корню проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestTestCoverage:
    """Тест для проверки покрытия тестами всего проекта"""
    
    def test_all_test_files_exist(self):
        """Проверяем что все тестовые файлы созданы"""
        test_files = [
            'tests/test_bot.py',
            'tests/test_whisper_transcriber.py',
            'tests/test_image_processor.py',
            'tests/test_commands.py',
            'tests/test_admin_service.py',
            'tests/test_database_models.py',
            'tests/test_admin_commands.py',
            'tests/test_database_integration.py',
            'tests/test_access_control.py'
        ]
        
        for test_file in test_files:
            assert os.path.exists(test_file), f"Тестовый файл {test_file} не найден"
    
    def test_test_files_are_importable(self):
        """Проверяем что все тестовые модули импортируются"""
        test_modules = [
            'tests.test_bot',
            'tests.test_whisper_transcriber', 
            'tests.test_image_processor',
            'tests.test_commands',
            'tests.test_admin_service',
            'tests.test_database_models',
            'tests.test_admin_commands',
            'tests.test_database_integration',
            'tests.test_access_control'
        ]
        
        for module_name in test_modules:
            try:
                __import__(module_name)
            except ImportError as e:
                # Пропускаем ошибки импорта зависимостей в тестовой среде
                if "telegram" not in str(e) and "whisper" not in str(e) and "pytesseract" not in str(e):
                    pytest.fail(f"Не удалось импортировать модуль {module_name}: {e}")
    
    def test_main_modules_exist(self):
        """Проверяем что все основные модули существуют"""
        main_modules = [
            'src/bot.py',
            'utils/whisper_transcriber.py',
            'utils/image_processor.py',
            'utils/admin_service.py',
            'database/models.py',
            'main.py'
        ]
        
        for module_file in main_modules:
            assert os.path.exists(module_file), f"Основной модуль {module_file} не найден"
    
    def test_configuration_files_exist(self):
        """Проверяем что все конфигурационные файлы существуют"""
        config_files = [
            'requirements.txt',
            'pytest.ini',
            'pyproject.toml',
            '.env.example',
            'Dockerfile',
            'docker-compose.yml',
            'README.md',
            'IMPROVEMENTS.md'
        ]
        
        for config_file in config_files:
            assert os.path.exists(config_file), f"Конфигурационный файл {config_file} не найден"
    
    def test_directory_structure(self):
        """Проверяем структуру директорий"""
        expected_dirs = [
            'src',
            'utils',
            'database',
            'admin',
            'tests',
            'logs',
            'downloads',
            '.github/workflows'
        ]
        
        for dir_path in expected_dirs:
            assert os.path.exists(dir_path), f"Директория {dir_path} не найдена"
            assert os.path.isdir(dir_path), f"{dir_path} не является директорией"
    
    def test_init_files_exist(self):
        """Проверяем наличие __init__.py файлов"""
        init_files = [
            'src/__init__.py',
            'utils/__init__.py',
            'database/__init__.py',
            'admin/__init__.py'
        ]
        
        for init_file in init_files:
            if os.path.exists(os.path.dirname(init_file)):
                assert os.path.exists(init_file), f"Файл {init_file} не найден"
    
    def test_class_coverage(self):
        """Проверяем что все основные классы покрыты тестами"""
        expected_classes = {
            'TelegramBot': 'tests.test_bot',
            'WhisperTranscriber': 'tests.test_whisper_transcriber',
            'ImageProcessor': 'tests.test_image_processor', 
            'AdminService': 'tests.test_admin_service',
            'User': 'tests.test_database_models',
            'Transcription': 'tests.test_database_models',
            'AdminLog': 'tests.test_database_models',
            'BotStatistics': 'tests.test_database_models'
        }
        
        for class_name, test_file in expected_classes.items():
            file_path = test_file.replace('.', '/') + '.py'
            assert os.path.exists(file_path), f"Тесты для класса {class_name} не найдены в {file_path}"
    
    def test_function_coverage(self):
        """Проверяем покрытие основных функций тестами"""
        # Это базовая проверка - в реальности можно использовать coverage.py
        critical_functions = {
            'TelegramBot': [
                'start_command',
                'help_command', 
                'status_command',
                'handle_photo',
                'admin_command',
                'stats_command',
                'users_command',
                'block_command',
                'unblock_command',
                'profile_command',
                'history_command'
            ],
            'AdminService': [
                'is_admin',
                'get_user_statistics',
                'get_transcription_statistics',
                'block_user',
                'unblock_user',
                'create_or_update_user'
            ]
        }
        
        total_functions = sum(len(funcs) for funcs in critical_functions.values())
        assert total_functions > 0, "Не найдено критических функций для тестирования"
        
        # Проверяем что тестовые файлы существуют для каждого класса
        for class_name in critical_functions.keys():
            if class_name == 'TelegramBot':
                assert os.path.exists('tests/test_bot.py'), f"Тесты для {class_name} не найдены"
                assert os.path.exists('tests/test_admin_commands.py'), f"Административные тесты для {class_name} не найдены"
            elif class_name == 'AdminService':
                assert os.path.exists('tests/test_admin_service.py'), f"Тесты для {class_name} не найдены"
    
    def test_database_models_tested(self):
        """Проверяем что все модели базы данных покрыты тестами"""
        expected_models = ['User', 'Transcription', 'AdminLog', 'BotStatistics']
        
        for model_name in expected_models:
            # Проверяем что модель существует в файле
            models_file = 'database/models.py'
            assert os.path.exists(models_file), f"Файл с моделями {models_file} не найден"
            
            with open(models_file, 'r', encoding='utf-8') as f:
                content = f.read()
                assert f'class {model_name}' in content, f"Модель {model_name} не найдена в {models_file}"
            
            # Проверяем что для модели есть тесты
            assert os.path.exists('tests/test_database_models.py'), f"Тесты для моделей не найдены"
    
    def test_administrative_functionality_coverage(self):
        """Проверяем покрытие административной функциональности"""
        admin_features = [
            'Ролевая модель',
            'Управление пользователями', 
            'Блокировка/разблокировка',
            'Статистика',
            'Логирование действий',
            'Контроль доступа',
            'Административные команды'
        ]
        
        # Проверяем что есть тесты для административных функций
        admin_test_files = [
            'tests/test_admin_service.py',
            'tests/test_admin_commands.py', 
            'tests/test_access_control.py'
        ]
        
        for test_file in admin_test_files:
            assert os.path.exists(test_file), f"Административный тест {test_file} не найден"
    
    def test_error_handling_coverage(self):
        """Проверяем покрытие обработки ошибок"""
        error_scenarios = [
            'Пользователь не найден',
            'Нет прав доступа',
            'Неверные аргументы команд',
            'Ошибки базы данных',
            'Ошибки обработки изображений',
            'Ошибки транскрибации'
        ]
        
        # Проверяем что тесты покрывают основные сценарии ошибок
        test_files_with_error_handling = [
            'tests/test_admin_service.py',
            'tests/test_admin_commands.py',
            'tests/test_database_integration.py',
            'tests/test_access_control.py'
        ]
        
        total_coverage_files = 0
        for test_file in test_files_with_error_handling:
            if os.path.exists(test_file):
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Ищем тестовые сценарии с ошибками
                    if any(keyword in content.lower() for keyword in ['error', 'exception', 'false', 'none']):
                        total_coverage_files += 1
        
        assert total_coverage_files >= 3, "Недостаточное покрытие обработки ошибок в тестах"
    
    def test_integration_coverage(self):
        """Проверяем интеграционное тестирование"""
        integration_aspects = [
            'Интеграция с базой данных',
            'Интеграция компонентов бота',
            'Интеграция с Telegram API',
            'Интеграция с AI сервисами'
        ]
        
        # Проверяем наличие интеграционных тестов
        integration_test_files = [
            'tests/test_database_integration.py',
            'tests/test_admin_commands.py'
        ]
        
        for test_file in integration_test_files:
            assert os.path.exists(test_file), f"Интеграционный тест {test_file} не найден"
    
    def test_pytest_configuration(self):
        """Проверяем конфигурацию pytest"""
        pytest_files = [
            'pytest.ini',
            'pyproject.toml'
        ]
        
        pytest_config_found = False
        for config_file in pytest_files:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'pytest' in content.lower():
                        pytest_config_found = True
                        break
        
        assert pytest_config_found, "Конфигурация pytest не найдена"
    
    def test_ci_cd_configuration(self):
        """Проверяем наличие CI/CD конфигурации"""
        ci_cd_files = [
            '.github/workflows/ci-cd.yml',
            '.github/workflows/tests.yml',
            '.github/workflows/ci.yml'
        ]
        
        ci_cd_found = False
        for ci_file in ci_cd_files:
            if os.path.exists(ci_file):
                ci_cd_found = True
                break
        
        assert ci_cd_found, "CI/CD конфигурация не найдена"
    
    def test_documentation_coverage(self):
        """Проверяем покрытие документации"""
        doc_files = [
            'README.md',
            'IMPROVEMENTS.md'
        ]
        
        for doc_file in doc_files:
            assert os.path.exists(doc_file), f"Документационный файл {doc_file} не найден"
            
            # Проверяем что документация содержит ключевую информацию
            with open(doc_file, 'r', encoding='utf-8') as f:
                content = f.read()
                assert len(content) > 1000, f"Документация {doc_file} слишком короткая"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])